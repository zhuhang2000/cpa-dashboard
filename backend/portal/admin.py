"""Admin JSON API: users, balances, redeem codes, prices and settings."""
from . import billing
from .billing import apply_credit
from .common import (DAY_MS, daily_series, day_start, epay_conf, like_pattern, money, month_start,
                     paginate, parse_money, tz_offset_ms, user_public)
from .constants import KeyStatus, RedeemStatus, Role, TxType, UserStatus
from .db import get_setting, now_ms, set_setting, transaction
from .keys import live_counts
from .security import new_redeem_code
from .web import ApiError

_RECHARGE_IN = "(%s)" % ", ".join("'%s'" % t for t in TxType.RECHARGE)


def overview(req):
    app = req.app
    conn = req.conn
    now = now_ms()
    today = day_start(app, now)
    month = month_start(app, now)
    start = today - 13 * DAY_MS

    def scalar(sql, args=()):
        return conn.execute(sql, args).fetchone()[0] or 0

    def recharge_since(since):
        return money(scalar("SELECT SUM(amount_micro) FROM transactions WHERE type IN %s "
                            "AND amount_micro > 0 AND created_at >= ?" % _RECHARGE_IN, (since,)))

    def usage_since(since):
        row = conn.execute("SELECT COUNT(*), COALESCE(SUM(cost_micro), 0) FROM usage_logs "
                           "WHERE ts >= ?", (since,)).fetchone()
        return {"requests": row[0], "cost": money(row[1])}

    offset = tz_offset_ms(app) // 1000
    usage_daily = conn.execute(
        "SELECT strftime('%Y-%m-%d', ts / 1000 + ?, 'unixepoch') AS d, COUNT(*) AS requests, "
        "SUM(cost_micro) AS cost FROM usage_logs WHERE ts >= ? GROUP BY d", (offset, start)
    ).fetchall()
    recharge_daily = conn.execute(
        "SELECT strftime('%%Y-%%m-%%d', created_at / 1000 + ?, 'unixepoch') AS d, "
        "SUM(amount_micro) AS recharge FROM transactions WHERE type IN %s AND amount_micro > 0 "
        "AND created_at >= ? GROUP BY d" % _RECHARGE_IN, (offset, start)
    ).fetchall()
    usage_series = daily_series(app, start, 14, usage_daily, {"requests": int, "cost": money})
    recharge_series = daily_series(app, start, 14, recharge_daily, {"recharge": money})
    for item, extra in zip(usage_series, recharge_series):
        item["recharge"] = extra["recharge"]

    top_users = conn.execute(
        "SELECT u.id, u.username, COUNT(*) AS requests, SUM(l.cost_micro) AS cost FROM usage_logs l "
        "JOIN users u ON u.id = l.user_id WHERE l.ts >= ? GROUP BY l.user_id "
        "ORDER BY cost DESC LIMIT 5", (month,)
    ).fetchall()
    unpriced = conn.execute(
        "SELECT model, COUNT(*) AS calls FROM usage_logs WHERE ts >= ? AND price_source = 'none' "
        "AND failed = 0 GROUP BY model ORDER BY calls DESC LIMIT 10", (now - DAY_MS,)
    ).fetchall()
    return {
        "users": {"total": scalar("SELECT COUNT(*) FROM users"),
                  "today": scalar("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today,))},
        "keys_active": scalar("SELECT COUNT(*) FROM api_keys WHERE status = ?", (KeyStatus.ACTIVE,)),
        "balance_total": money(scalar("SELECT SUM(balance_micro) FROM users")),
        "recharge": {"today": recharge_since(today), "month": recharge_since(month)},
        "usage": {"today": usage_since(today), "month": usage_since(month)},
        "daily": usage_series,
        "top_users": [{"id": r["id"], "username": r["username"], "requests": r["requests"],
                       "cost": money(r["cost"])} for r in top_users],
        "unpriced_models": [{"model": r["model"], "calls": r["calls"]} for r in unpriced],
        "sync": app.worker.state,
        "config": {
            "cpa_base_url": app.cpa.base,
            "cpa_configured": app.cpa.configured,
            "cpamp_usage_db": app.cfg["cpamp"].get("usage_db"),
            "online_payment": epay_conf(app) is not None,
        },
    }


# -- users ---------------------------------------------------------------------------
def list_users(req):
    page, size, offset = paginate(req)
    where, args = "1 = 1", []
    q = (req.arg("q") or "").strip()
    if q:
        where = "(u.username LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')"
        args = [like_pattern(q), like_pattern(q)]
    conn = req.conn
    total = conn.execute("SELECT COUNT(*) FROM users u WHERE " + where, args).fetchone()[0]
    rows = conn.execute(
        "SELECT u.* FROM users u WHERE " + where + " ORDER BY u.id DESC LIMIT ? OFFSET ?",
        args + [size, offset]
    ).fetchall()
    key_counts = live_counts(conn, [row["id"] for row in rows])
    items = []
    for row in rows:
        item = user_public(row)
        item.update(key_count=key_counts.get(row["id"], 0), last_login_ip=row["last_login_ip"] or "")
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": size}


def _get_user(conn, user_id):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "用户不存在")
    return row


def update_user(req, user_id):
    data = req.json()
    conn = req.conn
    row = _get_user(conn, user_id)
    is_self = row["id"] == req.user["id"]
    if "status" in data:
        if data["status"] not in UserStatus.ALL:
            raise ApiError(400, "状态不正确")
        if is_self and data["status"] != UserStatus.ACTIVE:
            raise ApiError(400, "不能禁用自己的账号")
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (data["status"], row["id"]))
        if data["status"] == UserStatus.BANNED:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
    if "role" in data:
        if data["role"] not in Role.ALL:
            raise ApiError(400, "角色不正确")
        if is_self and data["role"] != Role.ADMIN:
            raise ApiError(400, "不能取消自己的管理员身份")
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (data["role"], row["id"]))
    req.app.worker.trigger()
    return {"user": user_public(_get_user(conn, user_id))}


def adjust_balance(req, user_id):
    data = req.json()
    amount = parse_money(data.get("amount"), "调整金额", minimum=-1000000, maximum=1000000)
    note = str(data.get("note") or "").strip()[:100] or ("管理员充值" if amount > 0 else "管理员扣款")
    conn = req.conn
    with transaction(conn):
        _get_user(conn, user_id)
        balance = apply_credit(conn, user_id, amount, TxType.ADMIN, note=note, operator_id=req.user["id"])
    req.app.worker.trigger()
    return {"balance": money(balance)}


# -- redeem codes --------------------------------------------------------------------
def list_codes(req):
    page, size, offset = paginate(req)
    where, args = ["1 = 1"], []
    status = req.arg("status")
    if status in RedeemStatus.ALL:
        where.append("c.status = ?")
        args.append(status)
    batch = (req.arg("batch") or "").strip()
    if batch:
        where.append("c.batch = ?")
        args.append(batch)
    q = (req.arg("q") or "").strip().upper()
    if q:
        where.append("c.code LIKE ? ESCAPE '\\'")
        args.append(like_pattern(q))
    clause = " AND ".join(where)
    conn = req.conn
    total = conn.execute("SELECT COUNT(*) FROM redeem_codes c WHERE " + clause, args).fetchone()[0]
    rows = conn.execute(
        "SELECT c.*, u.username AS used_by_name FROM redeem_codes c "
        "LEFT JOIN users u ON u.id = c.used_by WHERE " + clause +
        " ORDER BY c.created_at DESC, c.code LIMIT ? OFFSET ?", args + [size, offset]
    ).fetchall()
    batches = [r[0] for r in conn.execute(
        "SELECT batch FROM redeem_codes WHERE batch IS NOT NULL AND batch != '' "
        "GROUP BY batch ORDER BY MAX(created_at) DESC LIMIT 50")]
    return {
        "items": [{"code": r["code"], "amount": money(r["amount_micro"]), "batch": r["batch"] or "",
                   "status": r["status"], "created_at": r["created_at"], "expires_at": r["expires_at"],
                   "used_by": r["used_by_name"] or "", "used_at": r["used_at"]} for r in rows],
        "total": total, "page": page, "page_size": size, "batches": batches,
    }


def create_codes(req):
    data = req.json()
    amount = parse_money(data.get("amount"), "面额", minimum=0.01, maximum=100000)
    try:
        count = int(data.get("count") or 1)
    except (TypeError, ValueError):
        raise ApiError(400, "数量格式不正确")
    if not 1 <= count <= 500:
        raise ApiError(400, "单次最多生成 500 个")
    batch = str(data.get("batch") or "").strip()[:32] or None
    expires_at = None
    if data.get("expires_days"):
        try:
            days = int(data["expires_days"])
        except (TypeError, ValueError):
            raise ApiError(400, "有效期格式不正确")
        if not 1 <= days <= 3650:
            raise ApiError(400, "有效期需在 1-3650 天之间")
        expires_at = now_ms() + days * DAY_MS
    codes = []
    conn = req.conn
    with transaction(conn):
        while len(codes) < count:
            code = new_redeem_code()
            inserted = conn.execute(
                "INSERT OR IGNORE INTO redeem_codes (code, amount_micro, batch, created_by, created_at, "
                "expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (code, amount, batch, req.user["id"], now_ms(), expires_at),
            ).rowcount
            if inserted:
                codes.append(code)
    return {"codes": codes, "amount": money(amount), "batch": batch or ""}


def disable_code(req, code):
    changed = req.conn.execute(
        "UPDATE redeem_codes SET status = ? WHERE code = ? AND status = ?",
        (RedeemStatus.DISABLED, code.upper(), RedeemStatus.UNUSED),
    ).rowcount
    if not changed:
        raise ApiError(400, "只能停用未使用的兑换码")
    return {"ok": True}


# -- prices --------------------------------------------------------------------------
def list_prices(req):
    app = req.app
    conn = req.conn
    cpamp = app.worker.cpamp_prices()
    book = billing.build_price_book(conn, cpamp, app.setting)
    # Raw CPAMP official price in USD / 1M tokens, without the selling multiplier.
    reference = billing.PriceBook({}, cpamp, 1.0, None)
    overrides = {r["model"]: r for r in conn.execute("SELECT * FROM model_prices")}
    seen = {r["model"]: r for r in conn.execute("SELECT * FROM seen_models")}
    hidden = set(get_setting(conn, "hidden_models", []) or [])
    items = []
    for model in sorted(set(overrides) | set(seen) | set(cpamp), key=str.lower):
        price, source = book.resolve(model)
        ref = reference.cpamp_price(model)
        override = overrides.get(model)
        usage = seen.get(model)
        items.append({
            "model": model,
            "source": source,
            "price": price.as_dict() if price else None,
            "cpamp": ref.as_dict() if ref else None,
            "override": None if override is None else {
                "input": override["input_price"], "output": override["output_price"],
                "cache_read": override["cache_read_price"], "cache_write": override["cache_write_price"],
                "note": override["note"] or "",
            },
            "hidden": model in hidden,
            "last_seen_ms": usage["last_seen_ms"] if usage else None,
            "calls": usage["calls"] if usage else 0,
        })
    return {"items": items, "cpamp_models": len(cpamp)}


def _price_value(data, name, label, optional=False):
    value = data.get(name)
    if value in (None, ""):
        if optional:
            return None
        raise ApiError(400, "请填写%s" % label)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "%s格式不正确" % label)
    if number < 0 or number != number or number > 1e6:
        raise ApiError(400, "%s超出范围" % label)
    return number


def upsert_price(req):
    data = req.json()
    model = str(data.get("model") or "").strip()
    if not model or len(model) > 128:
        raise ApiError(400, "模型名称需为 1-128 个字符")
    values = (
        _price_value(data, "input", "输入价格"),
        _price_value(data, "output", "输出价格"),
        _price_value(data, "cache_read", "缓存读取价格", optional=True),
        _price_value(data, "cache_write", "缓存写入价格", optional=True),
        str(data.get("note") or "").strip()[:100] or None,
    )
    conn = req.conn
    with transaction(conn):
        conn.execute("INSERT OR IGNORE INTO model_prices (model, updated_at) VALUES (?, ?)",
                     (model, now_ms()))
        conn.execute(
            "UPDATE model_prices SET input_price = ?, output_price = ?, cache_read_price = ?, "
            "cache_write_price = ?, note = ?, updated_at = ? WHERE model = ?",
            values + (now_ms(), model),
        )
    return {"ok": True}


def delete_price(req):
    model = str(req.json().get("model") or "")
    req.conn.execute("DELETE FROM model_prices WHERE model = ?", (model,))
    return {"ok": True}


def set_visibility(req):
    data = req.json()
    model = str(data.get("model") or "").strip()
    if not model:
        raise ApiError(400, "缺少模型名称")
    conn = req.conn
    with transaction(conn):
        hidden = set(get_setting(conn, "hidden_models", []) or [])
        if data.get("hidden"):
            hidden.add(model)
        else:
            hidden.discard(model)
        set_setting(conn, "hidden_models", sorted(hidden))
    return {"ok": True}


# -- settings & sync -----------------------------------------------------------------
def get_settings(req):
    return {"settings": req.app.all_settings()}


def put_settings(req):
    try:
        settings = req.app.update_settings(req.json())
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "设置格式不正确: %s" % exc)
    req.app.worker.invalidate_prices()
    return {"settings": settings}


def run_sync(req):
    worker = req.app.worker
    worker.reset_backoff()
    worker.invalidate_prices()
    worker.run_once()
    return {"sync": worker.state}


def register_routes(router):
    add = router.add
    add("GET", "/api/admin/overview", overview, auth="admin")
    add("GET", "/api/admin/users", list_users, auth="admin")
    add("PATCH", "/api/admin/users/<int:user_id>", update_user, auth="admin")
    add("POST", "/api/admin/users/<int:user_id>/balance", adjust_balance, auth="admin")
    add("GET", "/api/admin/codes", list_codes, auth="admin")
    add("POST", "/api/admin/codes", create_codes, auth="admin")
    add("DELETE", "/api/admin/codes/<code>", disable_code, auth="admin")
    add("GET", "/api/admin/prices", list_prices, auth="admin")
    add("PUT", "/api/admin/prices", upsert_price, auth="admin")
    add("POST", "/api/admin/prices/delete", delete_price, auth="admin")
    add("POST", "/api/admin/prices/visibility", set_visibility, auth="admin")
    add("GET", "/api/admin/settings", get_settings, auth="admin")
    add("PUT", "/api/admin/settings", put_settings, auth="admin")
    add("POST", "/api/admin/sync", run_sync, auth="admin")
