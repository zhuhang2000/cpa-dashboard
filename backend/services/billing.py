"""Balances, recharge codes and payment orders.

Balances use integer micro-units. Each operation that changes a balance owns its
transaction; apply_credit is the shared primitive for an existing transaction.
"""

import secrets
import time
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

from core.constants import OrderStatus, RedeemStatus, RedeemType, TxType
from core.db import like_pattern, now_ms, transaction
from core.errors import ApiError
from core.security import new_redeem_code
from integrations import epay

MICRO = 1000000
DAY_MS = 86400000


# ---- Shared ----


def to_micro(amount):
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid amount")
    if not value.is_finite():
        raise ValueError("invalid amount")
    return int((value * MICRO).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def from_micro(micro):
    return round((micro or 0) / MICRO, 6)


def money(micro):
    return from_micro(micro)


def parse_money(value, field="金额", minimum=None, maximum=None, allow_zero=False):
    if value is None or value == "":
        raise ApiError(400, "请填写%s" % field)
    try:
        micro = to_micro(value)
    except ValueError:
        raise ApiError(400, "%s格式不正确" % field)
    if micro == 0 and not allow_zero:
        raise ApiError(400, "%s不能为 0" % field)
    if minimum is not None and micro < to_micro(minimum):
        raise ApiError(400, "%s不能小于 %s" % (field, minimum))
    if maximum is not None and micro > to_micro(maximum):
        raise ApiError(400, "%s不能大于 %s" % (field, maximum))
    return micro


def apply_credit(conn, user_id, amount_micro, tx_type, ref=None, note=None, operator_id=None):
    """Change a balance and write its ledger row inside the caller's transaction."""
    recharge = amount_micro if (tx_type in TxType.RECHARGE and amount_micro > 0) else 0
    conn.execute(
        "UPDATE users SET balance_micro = balance_micro + ?, "
        "total_recharge_micro = total_recharge_micro + ? WHERE id = ?",
        (amount_micro, recharge, user_id),
    )
    balance = conn.execute("SELECT balance_micro FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount_micro, balance_after_micro, ref, note, "
        "operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, tx_type, amount_micro, balance, ref, note, operator_id, now_ms()),
    )
    return balance


def _ledger_item(row, admin):
    """A ledger row; administrators also see full redeem codes and who adjusted the balance."""
    ref = row["ref"] or ""
    if not admin and row["type"] in (TxType.REDEEM, TxType.REDEEM_GIFT) and len(ref) > 9:
        ref = ref[:4] + "-****-****-" + ref[-4:]
    item = {
        "id": row["id"],
        "type": row["type"],
        "amount": money(row["amount_micro"]),
        "balance_after": money(row["balance_after_micro"]),
        "ref": ref,
        "note": row["note"] or "",
        "created_at": row["created_at"],
    }
    if admin:
        item["operator"] = row["operator"] or ""
    return item


def list_transactions(conn, user_id, page, size, offset, admin=False):
    """A user's ledger; administrators also see full redeem codes and who adjusted it."""
    total = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    rows = conn.execute(
        "SELECT t.*, o.username AS operator FROM transactions t "
        "LEFT JOIN users o ON o.id = t.operator_id "
        "WHERE t.user_id = ? ORDER BY t.id DESC LIMIT ? OFFSET ?",
        (user_id, size, offset),
    ).fetchall()
    items = [_ledger_item(row, admin) for row in rows]
    return {"items": items, "total": total, "page": page, "page_size": size}


def epay_conf(cfg):
    conf = cfg["payment"]["epay"]
    return conf if conf["enabled"] else None


# ---- User operations ----


def _normalize_code(raw):
    compact = "".join(ch for ch in str(raw or "").upper() if ch.isalnum())
    if len(compact) == 16:
        return "-".join(compact[i : i + 4] for i in range(0, 16, 4))
    return str(raw or "").strip().upper()


def redeem(conn, user_id, raw_code, limiter, ip):
    code = _normalize_code(raw_code)
    if not code:
        raise ApiError(400, "请输入兑换码")
    fail_keys = ("redeem-user:%d" % user_id, "redeem-ip:" + ip)
    if limiter.count(fail_keys[0], 3600) >= 10 or limiter.count(fail_keys[1], 3600) >= 30:
        raise ApiError(429, "兑换失败次数过多，请 1 小时后再试")
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
            conn.execute(
                "UPDATE redeem_codes SET status = ?, used_by = ?, used_at = ? "
                "WHERE code = ? AND status = ?",
                (RedeemStatus.USED, user_id, now_ms(), code, RedeemStatus.UNUSED),
            )
            is_gift = row["type"] == RedeemType.GIFT
            balance = apply_credit(
                conn,
                user_id,
                row["amount_micro"],
                TxType.REDEEM_GIFT if is_gift else TxType.REDEEM,
                ref=code,
                note="兑换码赠送" if is_gift else "兑换码充值",
            )
    if error:
        for key in fail_keys:
            limiter.add(key)
        raise ApiError(400, error)
    return {"amount": money(row["amount_micro"]), "balance": money(balance)}


def list_orders(conn, user_id, page, size, offset):
    total = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, size, offset),
    ).fetchall()
    return {
        "items": [
            {
                "order_no": r["order_no"],
                "channel": r["channel"],
                "pay_amount": r["pay_amount"],
                "credit": money(r["credit_micro"]),
                "status": r["status"],
                "created_at": r["created_at"],
                "paid_at": r["paid_at"],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": size,
    }


def create_order(conn, cfg, setting, limiter, user_id, data, origin_url):
    conf = epay_conf(cfg)
    if conf is None:
        raise ApiError(400, "在线支付未开启，请使用兑换码充值")
    channel = str(data.get("channel") or "")
    if channel not in conf["channels"]:
        raise ApiError(400, "不支持的支付方式")
    pay = cfg["payment"]
    try:
        amount = Decimal(str(data.get("amount"))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError):
        raise ApiError(400, "金额格式不正确")
    if (
        not amount.is_finite()
        or amount < Decimal(str(pay["min_amount"]))
        or amount > Decimal(str(pay["max_amount"]))
    ):
        raise ApiError(400, "充值金额需在 %s - %s 之间" % (pay["min_amount"], pay["max_amount"]))
    if not limiter.allow("order:%d" % user_id, 20, 3600):
        raise ApiError(429, "下单过于频繁，请稍后再试")
    credit = to_micro(amount * Decimal(str(pay["credit_ratio"])))
    order_no = "P%s%06d" % (time.strftime("%Y%m%d%H%M%S"), secrets.randbelow(1000000))
    conn.execute(
        "INSERT INTO orders (order_no, user_id, channel, pay_amount, credit_micro, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (order_no, user_id, channel, str(amount), credit, now_ms()),
    )
    site = (conf["site_url"] or origin_url).rstrip("/")
    site_name = setting("site_name")
    pay_url = epay.build_pay_url(
        conf,
        channel,
        order_no,
        str(amount),
        "%s 余额充值" % site_name,
        site + "/api/pay/epay/notify",
        site + "/api/pay/epay/return",
        site_name,
    )
    return {"order_no": order_no, "pay_url": pay_url}


def settle_epay(conn, cfg, params):
    """Verify a gateway callback and credit once; return (ok, order_no, changed)."""
    conf = epay_conf(cfg)
    order_no = str(params.get("out_trade_no") or "")
    if conf is None or not epay.verify(params, conf["key"]):
        return False, order_no, False
    if str(params.get("pid")) != str(conf["pid"]) or params.get("trade_status") != "TRADE_SUCCESS":
        return False, order_no, False
    with transaction(conn):
        order = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
        if order is None:
            return False, order_no, False
        if order["status"] == OrderStatus.PAID:
            return True, order_no, False
        try:
            if Decimal(str(params.get("money"))) != Decimal(order["pay_amount"]):
                return False, order_no, False
        except InvalidOperation:
            return False, order_no, False
        conn.execute(
            "UPDATE orders SET status = ?, trade_no = ?, paid_at = ? "
            "WHERE order_no = ? AND status = ?",
            (
                OrderStatus.PAID,
                str(params.get("trade_no") or ""),
                now_ms(),
                order_no,
                OrderStatus.PENDING,
            ),
        )
        label = {"alipay": "支付宝", "wxpay": "微信支付", "qqpay": "QQ 钱包"}.get(
            order["channel"], order["channel"]
        )
        apply_credit(
            conn,
            order["user_id"],
            order["credit_micro"],
            TxType.ONLINE,
            ref=order_no,
            note="在线充值（%s）" % label,
        )
    return True, order_no, True


# ---- Administrator operations ----


def recharge_totals(conn, since):
    placeholders = ", ".join("?" for _ in TxType.RECHARGE)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_micro), 0) FROM transactions WHERE type IN (%s) "
        "AND amount_micro > 0 AND created_at >= ?" % placeholders,
        (*TxType.RECHARGE, since),
    ).fetchone()
    return row[0]


def recharge_daily(conn, start, tz_offset_minutes):
    placeholders = ", ".join("?" for _ in TxType.RECHARGE)
    return conn.execute(
        "SELECT strftime('%%Y-%%m-%%d', created_at / 1000 + ?, 'unixepoch') AS d, "
        "SUM(amount_micro) AS recharge FROM transactions WHERE type IN (%s) AND amount_micro > 0 "
        "AND created_at >= ? GROUP BY d" % placeholders,
        (tz_offset_minutes * 60, *TxType.RECHARGE, start),
    ).fetchall()


def adjust_balance(conn, user_id, operator_id, data, allow_gift=True):
    """Credit or debit a user by hand; without allow_gift a credit must be a recharge."""
    amount = parse_money(data.get("amount"), "调整金额", minimum=-1000000, maximum=1000000)
    tx_type, default_note = TxType.ADMIN, "管理员扣款"
    if amount > 0:
        credit_type = data.get("type")
        if credit_type not in RedeemType.ALL:
            raise ApiError(400, "请选择充值或赠送")
        if credit_type == RedeemType.GIFT:
            if not allow_gift:
                raise ApiError(403, "无权赠送余额，只能充值或扣款")
            tx_type, default_note = TxType.BONUS, "管理员赠送"
        else:
            default_note = "管理员充值"
    note = str(data.get("note") or "").strip()[:100] or default_note
    with transaction(conn):
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise ApiError(404, "用户不存在")
        balance = apply_credit(conn, user_id, amount, tx_type, note=note, operator_id=operator_id)
    return {"balance": money(balance)}


def list_all_transactions(conn, page, size, offset, filters):
    """Every user's ledger, newest first, with the totals of all the filtered entries.

    filters may hold q (part of the user's name or email), type, tag, operator (a user id) and
    start/end (epoch ms, end exclusive). tag keeps the users carrying it now, so an entry
    follows its user rather than the tag the user had when it was written. An unknown type is
    ignored, like the other list filters.
    operators lists everyone who has adjusted a balance, as the operator filter's choices.
    """
    where, args = ["1 = 1"], []
    query = (filters.get("q") or "").strip()
    if query:
        where.append("(u.username LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')")
        args += [like_pattern(query)] * 2
    if filters.get("type") in TxType.ALL:
        where.append("t.type = ?")
        args.append(filters["type"])
    tag = (filters.get("tag") or "").strip()
    if tag:
        where.append("u.tag = ?")
        args.append(tag)
    for field, expression in (
        ("operator", "t.operator_id = ?"),
        ("start", "t.created_at >= ?"),
        ("end", "t.created_at < ?"),
    ):
        if field in filters:
            where.append(expression)
            args.append(filters[field])
    clause = " AND ".join(where)
    totals = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(t.amount_micro), 0) AS net, "
        "COALESCE(SUM(CASE WHEN t.amount_micro > 0 THEN t.amount_micro END), 0) AS credit, "
        "COALESCE(SUM(CASE WHEN t.amount_micro < 0 THEN t.amount_micro END), 0) AS debit "
        "FROM transactions t JOIN users u ON u.id = t.user_id WHERE " + clause,
        args,
    ).fetchone()
    rows = conn.execute(
        "SELECT t.*, u.username, u.tag, o.username AS operator FROM transactions t "
        "JOIN users u ON u.id = t.user_id LEFT JOIN users o ON o.id = t.operator_id "
        "WHERE " + clause + " ORDER BY t.id DESC LIMIT ? OFFSET ?",
        args + [size, offset],
    ).fetchall()
    items = []
    for row in rows:
        item = _ledger_item(row, admin=True)
        item.update(user_id=row["user_id"], username=row["username"], tag=row["tag"] or "")
        items.append(item)
    operators = [
        {"id": row["id"], "username": row["username"], "role": row["role"]}
        for row in conn.execute(
            "SELECT DISTINCT o.id, o.username, o.role FROM transactions t "
            "JOIN users o ON o.id = t.operator_id ORDER BY o.username"
        )
    ]
    return {
        "items": items,
        "total": totals["n"],
        "sum_amount": money(totals["net"]),
        "sum_credit": money(totals["credit"]),
        "sum_debit": money(totals["debit"]),
        "operators": operators,
        "page": page,
        "page_size": size,
    }


def list_codes(conn, page, size, offset, status=None, batch="", query=""):
    where, args = ["1 = 1"], []
    if status in RedeemStatus.ALL:
        where.append("c.status = ?")
        args.append(status)
    batch = batch.strip()
    if batch:
        where.append("c.batch = ?")
        args.append(batch)
    query = query.strip().upper()
    if query:
        where.append("c.code LIKE ? ESCAPE '\\'")
        args.append(like_pattern(query))
    clause = " AND ".join(where)
    total = conn.execute("SELECT COUNT(*) FROM redeem_codes c WHERE " + clause, args).fetchone()[0]
    rows = conn.execute(
        "SELECT c.*, u.username AS used_by_name FROM redeem_codes c "
        "LEFT JOIN users u ON u.id = c.used_by WHERE "
        + clause
        + " ORDER BY c.created_at DESC, c.code LIMIT ? OFFSET ?",
        args + [size, offset],
    ).fetchall()
    batches = [
        r[0]
        for r in conn.execute(
            "SELECT batch FROM redeem_codes WHERE batch IS NOT NULL AND batch != '' "
            "GROUP BY batch ORDER BY MAX(created_at) DESC LIMIT 50"
        )
    ]
    return {
        "items": [
            {
                "code": r["code"],
                "amount": money(r["amount_micro"]),
                "type": r["type"],
                "batch": r["batch"] or "",
                "status": r["status"],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "used_by": r["used_by_name"] or "",
                "used_at": r["used_at"],
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": size,
        "batches": batches,
    }


def create_codes(conn, operator_id, data):
    """Generate unique recharge or gift codes in one transaction for the API and CLI."""
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
    code_type = data.get("type")
    if code_type not in RedeemType.ALL:
        raise ApiError(400, "兑换码类型必须为充值或赠送")
    codes = []
    with transaction(conn):
        while len(codes) < count:
            code = new_redeem_code()
            inserted = conn.execute(
                "INSERT OR IGNORE INTO redeem_codes (code, amount_micro, batch, created_by, created_at, "
                "expires_at, type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, amount, batch, operator_id, now_ms(), expires_at, code_type),
            ).rowcount
            if inserted:
                codes.append(code)
    return {"codes": codes, "amount": money(amount), "batch": batch or "", "type": code_type}


def delete_code(conn, code):
    changed = conn.execute(
        "DELETE FROM redeem_codes WHERE code = ? AND status IN (?, ?)",
        (code.upper(), RedeemStatus.UNUSED, RedeemStatus.DISABLED),
    ).rowcount
    if not changed:
        raise ApiError(400, "兑换码不存在或已使用，无法删除")
    return {"ok": True}


# ---- Sync worker and CLI ----


def charge_usage(conn, user_id, cost_micro):
    """Deduct a usage charge inside the transaction that records the event."""
    if cost_micro:
        conn.execute(
            "UPDATE users SET balance_micro = balance_micro - ?, "
            "total_spent_micro = total_spent_micro + ? WHERE id = ?",
            (cost_micro, cost_micro, user_id),
        )
