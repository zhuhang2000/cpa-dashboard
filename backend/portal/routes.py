"""User-facing JSON API."""
import csv
import io
import secrets
import time
import urllib.parse
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from . import __version__, billing, epay, keys
from .billing import MICRO, apply_credit, to_micro
from .common import (DAY_MS, EMAIL_RE, USERNAME_RE, daily_series, day_start, epay_conf, money,
                     month_start, paginate, time_label, tz_offset_ms, user_public)
from .constants import OrderStatus, RedeemStatus, TxType, UserStatus
from .db import get_setting, now_ms, transaction
from .security import hash_password, new_session_token, sha256_hex, verify_password
from .web import SESSION_COOKIE, ApiError, Response

_DUMMY_HASH = []


def _dummy_hash():
    if not _DUMMY_HASH:
        _DUMMY_HASH.append(hash_password(secrets.token_hex(8)))
    return _DUMMY_HASH[0]


# -- public --------------------------------------------------------------------------
def get_status(req):
    app = req.app
    pay = app.cfg["payment"]
    conf = epay_conf(app)
    return {
        "site_name": app.setting("site_name"),
        "public_api_base": app.setting("public_api_base"),
        "guide_url": app.cfg["guide_url"],
        "announcement": app.setting("announcement"),
        "allow_register": bool(app.setting("allow_register")),
        "signup_bonus": app.setting("signup_bonus"),
        "currency_symbol": app.cfg["currency_symbol"],
        "max_keys_per_user": keys.max_keys(app),
        "payment": {
            "online": conf is not None,
            "channels": list(conf.get("channels") or []) if conf else [],
            "presets": pay.get("presets") or [],
            "min_amount": pay.get("min_amount"),
            "max_amount": pay.get("max_amount"),
            "credit_ratio": pay.get("credit_ratio") or 1,
        },
        "version": __version__,
    }


def get_pricing(req):
    app = req.app
    conn = req.conn
    cpamp = app.worker.cpamp_prices()
    book = billing.build_price_book(conn, cpamp, app.setting)
    notes = {row["model"]: row["note"] for row in conn.execute("SELECT model, note FROM model_prices")}
    hidden = set(get_setting(conn, "hidden_models", []) or [])
    since = now_ms() - 30 * DAY_MS
    models = set(notes) | set(cpamp)
    models.update(row[0] for row in conn.execute(
        "SELECT model FROM seen_models WHERE last_seen_ms >= ? AND model != 'unknown'", (since,)))
    items = []
    for model in sorted(models, key=str.lower):
        if model in hidden:
            continue
        price, source = book.resolve(model)
        if price is None:
            continue
        item = price.as_dict()
        item.update(model=model, note=notes.get(model) or "", source=source)
        items.append(item)
    return {"items": items, "currency_symbol": app.cfg["currency_symbol"]}


# -- auth ----------------------------------------------------------------------------
def _start_session(req, user_id):
    token = new_session_token()
    lifetime = int(req.app.cfg.get("session_days") or 7) * DAY_MS
    now = now_ms()
    req.conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    req.conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at, ip, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (sha256_hex(token), user_id, now, now + lifetime, req.ip,
         (req.headers.get("User-Agent") or "")[:200]),
    )
    req.set_cookie(SESSION_COOKIE, token, lifetime // 1000)


def _validate_password(password):
    if len(password) < 8:
        raise ApiError(400, "密码至少 8 位")
    if len(password) > 128:
        raise ApiError(400, "密码过长")


def register(req):
    app = req.app
    if not app.setting("allow_register"):
        raise ApiError(403, "当前未开放注册")
    data = req.json()
    username = str(data.get("username") or "").strip()
    email = str(data.get("email") or "").strip() or None
    password = str(data.get("password") or "")
    if not USERNAME_RE.match(username):
        raise ApiError(400, "用户名需为 3-32 位字母、数字、下划线或短横线")
    if email is not None and not EMAIL_RE.match(email):
        raise ApiError(400, "邮箱格式不正确")
    _validate_password(password)
    if not app.limiter.allow("register:" + req.ip, 10, 3600):
        raise ApiError(429, "注册过于频繁，请稍后再试")

    password_hash = hash_password(password)
    bonus = to_micro(app.setting("signup_bonus") or 0)
    conn = req.conn
    with transaction(conn):
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise ApiError(409, "用户名已被占用")
        if email and conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise ApiError(409, "该邮箱已注册")
        user_id = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at, last_login_at, "
            "last_login_ip) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, password_hash, now_ms(), now_ms(), req.ip),
        ).lastrowid
        if bonus > 0:
            apply_credit(conn, user_id, bonus, TxType.BONUS, note="注册赠送")
        _start_session(req, user_id)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": user_public(row)}


def login(req):
    app = req.app
    data = req.json()
    account = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if not account or not password:
        raise ApiError(400, "请输入用户名和密码")
    ip_key = "login-ip:" + req.ip
    account_key = "login-account:" + account.lower()
    if app.limiter.count(ip_key, 600) >= 20 or app.limiter.count(account_key, 600) >= 10:
        raise ApiError(429, "登录失败次数过多，请 10 分钟后再试")

    conn = req.conn
    row = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?",
                       (account, account)).fetchone()
    valid = verify_password(password, row["password_hash"] if row else _dummy_hash())
    if row is None or not valid:
        app.limiter.add(ip_key)
        app.limiter.add(account_key)
        raise ApiError(401, "用户名或密码错误")
    if row["status"] != UserStatus.ACTIVE:
        raise ApiError(403, "账号已被禁用，请联系管理员")
    app.limiter.reset(account_key)
    with transaction(conn):
        conn.execute("UPDATE users SET last_login_at = ?, last_login_ip = ? WHERE id = ?",
                     (now_ms(), req.ip, row["id"]))
        _start_session(req, row["id"])
    row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
    return {"user": user_public(row)}


def logout(req):
    if req.session_hash:
        req.conn.execute("DELETE FROM sessions WHERE token_hash = ?", (req.session_hash,))
    req.clear_cookie(SESSION_COOKIE)
    return {"ok": True}


# -- account -------------------------------------------------------------------------
def get_me(req):
    user = req.user
    if user is None:  # lets the SPA probe the session without a 401 in the console
        return {"user": None, "key_count": 0}
    return {"user": user_public(user), "key_count": keys.count_live(req.conn, user["id"])}


def update_profile(req):
    data = req.json()
    email = str(data.get("email") or "").strip() or None
    if email is not None and not EMAIL_RE.match(email):
        raise ApiError(400, "邮箱格式不正确")
    conn = req.conn
    with transaction(conn):
        if email and conn.execute("SELECT 1 FROM users WHERE email = ? AND id != ?",
                                  (email, req.user["id"])).fetchone():
            raise ApiError(409, "该邮箱已被其他账号使用")
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, req.user["id"]))
    row = conn.execute("SELECT * FROM users WHERE id = ?", (req.user["id"],)).fetchone()
    return {"user": user_public(row)}


def change_password(req):
    data = req.json()
    old = str(data.get("old_password") or "")
    new = str(data.get("new_password") or "")
    if not verify_password(old, req.user["password_hash"]):
        raise ApiError(400, "当前密码不正确")
    _validate_password(new)
    password_hash = hash_password(new)
    with transaction(req.conn):
        req.conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (password_hash, req.user["id"]))
        req.conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                         (req.user["id"], req.session_hash))
    return {"ok": True}


# -- API keys ------------------------------------------------------------------------
def list_keys(req):
    rows = keys.list_for_user(req.conn, req.user["id"])
    return {"items": [keys.to_public(req.app, row, req.user) for row in rows],
            "max_keys": keys.max_keys(req.app)}


def create_key(req):
    row = keys.create(req.conn, req.app, req.user["id"], req.json())
    req.app.worker.trigger()
    return {"key": row["key"], "item": keys.to_public(req.app, row, req.user)}


def update_key(req, key_id):
    row = keys.get_owned(req.conn, req.user["id"], key_id)
    row = keys.update(req.conn, row, req.json())
    req.app.worker.trigger()
    return {"item": keys.to_public(req.app, row, req.user)}


def delete_key(req, key_id):
    keys.soft_delete(req.conn, keys.get_owned(req.conn, req.user["id"], key_id))
    req.app.worker.trigger()
    return {"ok": True}


def reveal_key(req, key_id):
    return {"key": keys.get_owned(req.conn, req.user["id"], key_id)["key"]}


# -- usage ---------------------------------------------------------------------------
def usage_summary(req):
    app = req.app
    conn = req.conn
    uid = req.user["id"]
    days = req.int_arg("days", 30, 1, 90)
    now = now_ms()
    today = day_start(app, now)
    start = today - (days - 1) * DAY_MS

    def totals(since):
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cost_micro), 0) AS cost, "
            "COALESCE(SUM(total_tokens), 0) AS tokens FROM usage_logs WHERE user_id = ? AND ts >= ?",
            (uid, since),
        ).fetchone()
        return {"requests": row["n"], "cost": money(row["cost"]), "tokens": row["tokens"]}

    daily = conn.execute(
        "SELECT strftime('%Y-%m-%d', ts / 1000 + ?, 'unixepoch') AS d, COUNT(*) AS requests, "
        "SUM(cost_micro) AS cost, SUM(total_tokens) AS tokens, "
        "SUM(input_tokens + cache_read_tokens + cache_write_tokens) AS input_tokens, "
        "SUM(output_tokens) AS output_tokens, SUM(failed) AS failed "
        "FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY d",
        (tz_offset_ms(app) // 1000, uid, start),
    ).fetchall()
    by_model = conn.execute(
        "SELECT model, COUNT(*) AS requests, SUM(cost_micro) AS cost, SUM(total_tokens) AS tokens "
        "FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY model "
        "ORDER BY cost DESC, requests DESC LIMIT 8",
        (uid, start),
    ).fetchall()
    by_key = conn.execute(
        "SELECT l.key_id, k.name, COUNT(*) AS requests, SUM(l.cost_micro) AS cost "
        "FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
        "WHERE l.user_id = ? AND l.ts >= ? GROUP BY l.key_id ORDER BY cost DESC LIMIT 8",
        (uid, start),
    ).fetchall()
    total_requests = conn.execute("SELECT COUNT(*) FROM usage_logs WHERE user_id = ?",
                                  (uid,)).fetchone()[0]
    return {
        "balance": money(req.user["balance_micro"]),
        "today": totals(today),
        "month": totals(month_start(app, now)),
        "range": totals(start),
        "total": {"requests": total_requests, "cost": money(req.user["total_spent_micro"])},
        "days": days,
        "daily": daily_series(app, start, days, daily, {
            "requests": int, "cost": money, "tokens": int, "input_tokens": int,
            "output_tokens": int, "failed": int,
        }),
        "by_model": [{"model": r["model"], "requests": r["requests"], "cost": money(r["cost"]),
                      "tokens": r["tokens"] or 0} for r in by_model],
        "by_key": [{"key_id": r["key_id"], "name": r["name"] or "已删除密钥",
                    "requests": r["requests"], "cost": money(r["cost"])} for r in by_key],
    }


def _usage_where(req):
    where = ["l.user_id = ?"]
    args = [req.user["id"]]
    key_id = req.arg("key_id")
    if key_id:
        where.append("l.key_id = ?")
        args.append(req.int_arg("key_id", 0))
    model = req.arg("model")
    if model:
        where.append("l.model = ?")
        args.append(model)
    start = req.arg("start")
    if start:
        where.append("l.ts >= ?")
        args.append(req.int_arg("start", 0))
    end = req.arg("end")
    if end:
        where.append("l.ts < ?")
        args.append(req.int_arg("end", 0))
    status = req.arg("status")
    if status in ("success", "failed"):
        where.append("l.failed = ?")
        args.append(1 if status == "failed" else 0)
    return " AND ".join(where), args


def _usage_item(row):
    return {
        "id": row["id"],
        "ts": row["ts"],
        "key_id": row["key_id"],
        "key_name": row["key_name"] or "已删除密钥",
        "model": row["model"],
        "endpoint": row["endpoint"] or "",
        "input_tokens": row["input_tokens"],
        "cache_read_tokens": row["cache_read_tokens"],
        "cache_write_tokens": row["cache_write_tokens"],
        "output_tokens": row["output_tokens"],
        "reasoning_tokens": row["reasoning_tokens"],
        "total_tokens": row["total_tokens"],
        "cost": money(row["cost_micro"]),
        "failed": bool(row["failed"]),
        "latency_ms": row["latency_ms"],
        "stream": None if row["stream"] is None else bool(row["stream"]),
    }


def usage_logs(req):
    where, args = _usage_where(req)
    page, size, offset = paginate(req)
    conn = req.conn
    summary = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_micro), 0) AS cost, "
        "COALESCE(SUM(total_tokens), 0) AS tokens FROM usage_logs l WHERE " + where, args
    ).fetchone()
    rows = conn.execute(
        "SELECT l.*, k.name AS key_name FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
        "WHERE " + where + " ORDER BY l.ts DESC, l.id DESC LIMIT ? OFFSET ?",
        args + [size, offset],
    ).fetchall()
    models = [r[0] for r in conn.execute(
        "SELECT model FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY model ORDER BY model",
        (req.user["id"], now_ms() - 90 * DAY_MS))]
    return {
        "items": [_usage_item(row) for row in rows],
        "total": summary["n"],
        "sum_cost": money(summary["cost"]),
        "sum_tokens": summary["tokens"],
        "page": page,
        "page_size": size,
        "models": models,
    }


def usage_export(req):
    where, args = _usage_where(req)
    rows = req.conn.execute(
        "SELECT l.*, k.name AS key_name FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
        "WHERE " + where + " ORDER BY l.ts DESC, l.id DESC LIMIT 100000",
        args,
    ).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["时间", "密钥", "模型", "输入 tokens", "缓存读取 tokens", "缓存写入 tokens",
                     "输出 tokens", "总 tokens", "费用", "状态", "耗时(ms)"])
    for row in rows:
        writer.writerow([
            time_label(req.app, row["ts"]), row["key_name"] or "已删除密钥", row["model"],
            row["input_tokens"], row["cache_read_tokens"], row["cache_write_tokens"],
            row["output_tokens"], row["total_tokens"], "%.6f" % (row["cost_micro"] / MICRO),
            "失败" if row["failed"] else "成功", row["latency_ms"] if row["latency_ms"] is not None else "",
        ])
    filename = "usage-%s.csv" % time.strftime("%Y%m%d-%H%M%S")
    return Response(("﻿" + out.getvalue()).encode("utf-8"), 200, "text/csv; charset=utf-8",
                    [("Content-Disposition", 'attachment; filename="%s"' % filename),
                     ("Cache-Control", "no-store")])


# -- billing -------------------------------------------------------------------------
def list_transactions(req):
    page, size, offset = paginate(req)
    conn = req.conn
    total = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?",
                         (req.user["id"],)).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
        (req.user["id"], size, offset),
    ).fetchall()
    items = []
    for row in rows:
        ref = row["ref"] or ""
        if row["type"] == TxType.REDEEM and len(ref) > 9:
            ref = ref[:4] + "-****-****-" + ref[-4:]
        items.append({"id": row["id"], "type": row["type"], "amount": money(row["amount_micro"]),
                      "balance_after": money(row["balance_after_micro"]), "ref": ref,
                      "note": row["note"] or "", "created_at": row["created_at"]})
    return {"items": items, "total": total, "page": page, "page_size": size}


def _normalize_code(raw):
    compact = "".join(ch for ch in str(raw or "").upper() if ch.isalnum())
    if len(compact) == 16:
        return "-".join(compact[i:i + 4] for i in range(0, 16, 4))
    return str(raw or "").strip().upper()


def redeem(req):
    app = req.app
    uid = req.user["id"]
    code = _normalize_code(req.json().get("code"))
    if not code:
        raise ApiError(400, "请输入兑换码")
    fail_keys = ("redeem-user:%d" % uid, "redeem-ip:" + req.ip)
    if app.limiter.count(fail_keys[0], 3600) >= 10 or app.limiter.count(fail_keys[1], 3600) >= 30:
        raise ApiError(429, "兑换失败次数过多，请 1 小时后再试")
    conn = req.conn
    error = None
    with transaction(conn):
        row = conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (code,)).fetchone()
        if row is None:
            error = "兑换码不存在"
        elif row["status"] == RedeemStatus.USED:
            error = "兑换码已被使用"
        elif row["status"] != RedeemStatus.UNUSED:
            error = "兑换码已停用"
        elif row["expires_at"] and row["expires_at"] <= now_ms():
            error = "兑换码已过期"
        else:
            conn.execute("UPDATE redeem_codes SET status = ?, used_by = ?, used_at = ? "
                         "WHERE code = ? AND status = ?",
                         (RedeemStatus.USED, uid, now_ms(), code, RedeemStatus.UNUSED))
            balance = apply_credit(conn, uid, row["amount_micro"], TxType.REDEEM, ref=code,
                                   note="兑换码充值")
    if error:
        for key in fail_keys:
            app.limiter.add(key)
        raise ApiError(400, error)
    app.worker.trigger()
    return {"amount": money(row["amount_micro"]), "balance": money(balance)}


def list_orders(req):
    page, size, offset = paginate(req)
    conn = req.conn
    total = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?",
                         (req.user["id"],)).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (req.user["id"], size, offset),
    ).fetchall()
    return {
        "items": [{"order_no": r["order_no"], "channel": r["channel"], "pay_amount": r["pay_amount"],
                   "credit": money(r["credit_micro"]), "status": r["status"],
                   "created_at": r["created_at"], "paid_at": r["paid_at"]} for r in rows],
        "total": total, "page": page, "page_size": size,
    }


def create_order(req):
    app = req.app
    conf = epay_conf(app)
    if conf is None:
        raise ApiError(400, "在线支付未开启，请使用兑换码充值")
    data = req.json()
    channel = str(data.get("channel") or "")
    if channel not in (conf.get("channels") or []):
        raise ApiError(400, "不支持的支付方式")
    pay = app.cfg["payment"]
    try:
        amount = Decimal(str(data.get("amount"))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError):
        raise ApiError(400, "金额格式不正确")
    if not amount.is_finite() or amount < Decimal(str(pay.get("min_amount") or 1)) or \
            amount > Decimal(str(pay.get("max_amount") or 10000)):
        raise ApiError(400, "充值金额需在 %s - %s 之间" % (pay.get("min_amount"), pay.get("max_amount")))
    if not app.limiter.allow("order:%d" % req.user["id"], 20, 3600):
        raise ApiError(429, "下单过于频繁，请稍后再试")
    credit = to_micro(amount * Decimal(str(pay.get("credit_ratio") or 1)))
    order_no = "P%s%06d" % (time.strftime("%Y%m%d%H%M%S"), secrets.randbelow(1000000))
    req.conn.execute(
        "INSERT INTO orders (order_no, user_id, channel, pay_amount, credit_micro, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (order_no, req.user["id"], channel, str(amount), credit, now_ms()),
    )
    site = (conf.get("site_url") or req.origin_url()).rstrip("/")
    site_name = app.setting("site_name")
    pay_url = epay.build_pay_url(conf, channel, order_no, str(amount), "%s 余额充值" % site_name,
                                 site + "/api/pay/epay/notify", site + "/api/pay/epay/return",
                                 site_name)
    return {"order_no": order_no, "pay_url": pay_url}


def _settle_epay(app, params):
    """Verify a gateway callback and credit the order once. Returns (ok, order_no)."""
    conf = epay_conf(app)
    order_no = str(params.get("out_trade_no") or "")
    if conf is None or not epay.verify(params, conf["key"]):
        return False, order_no
    if str(params.get("pid")) != str(conf["pid"]) or params.get("trade_status") != "TRADE_SUCCESS":
        return False, order_no
    conn = app.db()
    try:
        with transaction(conn):
            order = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
            if order is None:
                return False, order_no
            if order["status"] == OrderStatus.PAID:
                return True, order_no
            try:
                if Decimal(str(params.get("money"))) != Decimal(order["pay_amount"]):
                    return False, order_no
            except InvalidOperation:
                return False, order_no
            conn.execute("UPDATE orders SET status = ?, trade_no = ?, paid_at = ? "
                         "WHERE order_no = ? AND status = ?",
                         (OrderStatus.PAID, str(params.get("trade_no") or ""), now_ms(), order_no,
                          OrderStatus.PENDING))
            label = {"alipay": "支付宝", "wxpay": "微信支付", "qqpay": "QQ 钱包"}.get(order["channel"],
                                                                              order["channel"])
            apply_credit(conn, order["user_id"], order["credit_micro"], TxType.ONLINE, ref=order_no,
                         note="在线充值（%s）" % label)
    finally:
        conn.close()
    app.worker.trigger()
    return True, order_no


def _callback_params(req):
    params = dict(req.query)
    ctype = (req.headers.get("Content-Type") or "").lower()
    if req.body and "application/x-www-form-urlencoded" in ctype:
        form = urllib.parse.parse_qs(req.body.decode("utf-8", "replace"), keep_blank_values=True)
        params.update({k: v[-1] for k, v in form.items()})
    return params


def epay_notify(req):
    ok, _ = _settle_epay(req.app, _callback_params(req))
    return Response.text("success" if ok else "fail")


def epay_return(req):
    ok, order_no = _settle_epay(req.app, _callback_params(req))
    query = urllib.parse.urlencode({"order": order_no, "result": "success" if ok else "pending"})
    return Response.redirect("/recharge?" + query)


def register_routes(router):
    add = router.add
    add("GET", "/api/status", get_status, auth=None)
    add("GET", "/api/pricing", get_pricing, auth=None)
    add("POST", "/api/auth/register", register, auth=None)
    add("POST", "/api/auth/login", login, auth=None)
    add("POST", "/api/auth/logout", logout, auth=None)
    add("GET", "/api/user/me", get_me, auth=None)
    add("PUT", "/api/user/profile", update_profile)
    add("POST", "/api/user/password", change_password)
    add("GET", "/api/keys", list_keys)
    add("POST", "/api/keys", create_key)
    add("PATCH", "/api/keys/<int:key_id>", update_key)
    add("DELETE", "/api/keys/<int:key_id>", delete_key)
    add("POST", "/api/keys/<int:key_id>/reveal", reveal_key)
    add("GET", "/api/usage/summary", usage_summary)
    add("GET", "/api/usage/logs", usage_logs)
    add("GET", "/api/usage/export", usage_export)
    add("GET", "/api/billing/transactions", list_transactions)
    add("POST", "/api/billing/redeem", redeem)
    add("GET", "/api/billing/orders", list_orders)
    add("POST", "/api/billing/orders", create_order)
    add("GET", "/api/pay/epay/notify", epay_notify, auth=None, raw=True)
    add("POST", "/api/pay/epay/notify", epay_notify, auth=None, raw=True)
    add("GET", "/api/pay/epay/return", epay_return, auth=None, raw=True)
