"""Usage ingestion, history queries and reporting.

This service owns usage_logs and the CPAMP ingestion cursor. A usage batch is
one transaction, including balance debits, key counters and discovered models.
Reporting reads can aggregate data belonging to other business modules.
"""

import datetime

from core.db import get_setting, now_ms, set_setting, transaction
from services import accounts, api_keys, billing, pricing

DAY_MS = 86400000
KEY_CLOCK_SKEW_MS = 5 * 60 * 1000


# ---- Shared ----


def day_start(ts, tz_offset_minutes):
    offset = tz_offset_minutes * 60000
    return ((ts + offset) // DAY_MS) * DAY_MS - offset


def month_start(ts, tz_offset_minutes):
    offset = tz_offset_minutes * 60000
    local = datetime.datetime.fromtimestamp((ts + offset) / 1000, tz=datetime.timezone.utc)
    first = datetime.datetime(local.year, local.month, 1, tzinfo=datetime.timezone.utc)
    return int(first.timestamp() * 1000) - offset


def list_logs(conn, user_id, filters, size, offset):
    """Return a filtered page, aggregate totals and recent model names."""
    where, args = _where(user_id, filters)
    totals = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_micro), 0) AS cost, "
        "COALESCE(SUM(total_tokens), 0) AS tokens FROM usage_logs l WHERE " + where,
        args,
    ).fetchone()
    rows = conn.execute(
        "SELECT l.*, k.name AS key_name FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
        "WHERE " + where + " ORDER BY l.ts DESC, l.id DESC LIMIT ? OFFSET ?",
        args + [size, offset],
    ).fetchall()
    models = [
        row[0]
        for row in conn.execute(
            "SELECT model FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY model ORDER BY model",
            (user_id, now_ms() - 90 * DAY_MS),
        )
    ]
    return {"items": [dict(row) for row in rows], "summary": dict(totals), "models": models}


def _where(user_id, filters):
    where, args = ["l.user_id = ?"], [user_id]
    for field, expression in (
        ("key_id", "l.key_id = ?"),
        ("model", "l.model = ?"),
        ("start", "l.ts >= ?"),
        ("end", "l.ts < ?"),
    ):
        if field in filters:
            where.append(expression)
            args.append(filters[field])
    if filters.get("status") in ("success", "failed"):
        where.append("l.failed = ?")
        args.append(1 if filters["status"] == "failed" else 0)
    return " AND ".join(where), args


# ---- User operations ----


def summary(conn, user_id, days, tz_offset_minutes, now=None):
    """Return report data; monetary values remain integer micro-units."""
    now = now_ms() if now is None else now
    today = day_start(now, tz_offset_minutes)
    start = today - (days - 1) * DAY_MS

    def totals(since):
        return dict(
            conn.execute(
                "SELECT COUNT(*) AS requests, COALESCE(SUM(cost_micro), 0) AS cost, "
                "COALESCE(SUM(total_tokens), 0) AS tokens FROM usage_logs WHERE user_id = ? AND ts >= ?",
                (user_id, since),
            ).fetchone()
        )

    daily = conn.execute(
        "SELECT strftime('%Y-%m-%d', ts / 1000 + ?, 'unixepoch') AS d, COUNT(*) AS requests, "
        "SUM(cost_micro) AS cost, SUM(total_tokens) AS tokens, "
        "SUM(input_tokens + cache_read_tokens + cache_write_tokens) AS input_tokens, "
        "SUM(output_tokens) AS output_tokens, SUM(failed) AS failed "
        "FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY d",
        (tz_offset_minutes * 60, user_id, start),
    ).fetchall()
    by_model = conn.execute(
        "SELECT model, COUNT(*) AS requests, SUM(cost_micro) AS cost, SUM(total_tokens) AS tokens "
        "FROM usage_logs WHERE user_id = ? AND ts >= ? GROUP BY model "
        "ORDER BY cost DESC, requests DESC LIMIT 8",
        (user_id, start),
    ).fetchall()
    by_key = conn.execute(
        "SELECT l.key_id, k.name, COUNT(*) AS requests, SUM(l.cost_micro) AS cost "
        "FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
        "WHERE l.user_id = ? AND l.ts >= ? GROUP BY l.key_id ORDER BY cost DESC LIMIT 8",
        (user_id, start),
    ).fetchall()
    return {
        "today": totals(today),
        "month": totals(month_start(now, tz_offset_minutes)),
        "range": totals(start),
        "start": start,
        "total_requests": conn.execute(
            "SELECT COUNT(*) FROM usage_logs WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0],
        "daily": [dict(row) for row in daily],
        "by_model": [dict(row) for row in by_model],
        "by_key": [dict(row) for row in by_key],
    }


def export_logs(conn, user_id, filters):
    where, args = _where(user_id, filters)
    return [
        dict(row)
        for row in conn.execute(
            "SELECT l.*, k.name AS key_name FROM usage_logs l LEFT JOIN api_keys k ON k.id = l.key_id "
            "WHERE " + where + " ORDER BY l.ts DESC, l.id DESC LIMIT 100000",
            args,
        )
    ]


# ---- Administrator operations ----


def overview(conn, tz_offset_minutes, now=None):
    """Return operational statistics without HTTP or worker-state concerns."""
    now = now_ms() if now is None else now
    today = day_start(now, tz_offset_minutes)
    month = month_start(now, tz_offset_minutes)
    start = today - 13 * DAY_MS

    def totals(since):
        return dict(
            conn.execute(
                "SELECT COUNT(*) AS requests, COALESCE(SUM(cost_micro), 0) AS cost "
                "FROM usage_logs WHERE ts >= ?",
                (since,),
            ).fetchone()
        )

    daily = conn.execute(
        "SELECT strftime('%Y-%m-%d', ts / 1000 + ?, 'unixepoch') AS d, COUNT(*) AS requests, "
        "SUM(cost_micro) AS cost FROM usage_logs WHERE ts >= ? GROUP BY d",
        (tz_offset_minutes * 60, start),
    ).fetchall()
    top_users = conn.execute(
        "SELECT u.id, u.username, COUNT(*) AS requests, SUM(l.cost_micro) AS cost FROM usage_logs l "
        "JOIN users u ON u.id = l.user_id WHERE l.ts >= ? GROUP BY l.user_id "
        "ORDER BY cost DESC LIMIT 5",
        (month,),
    ).fetchall()
    unpriced = conn.execute(
        "SELECT model, COUNT(*) AS calls FROM usage_logs WHERE ts >= ? AND price_source = 'none' "
        "AND failed = 0 GROUP BY model ORDER BY calls DESC LIMIT 10",
        (now - DAY_MS,),
    ).fetchall()
    return {
        "users": accounts.overview_counts(conn, today),
        "keys_active": api_keys.active_count(conn),
        "recharge": {
            "today": billing.recharge_totals(conn, today),
            "month": billing.recharge_totals(conn, month),
        },
        "usage": {"today": totals(today), "month": totals(month)},
        "start": start,
        "daily": [dict(row) for row in daily],
        "recharge_daily": billing.recharge_daily(conn, start, tz_offset_minutes),
        "top_users": [dict(row) for row in top_users],
        "unpriced_models": [dict(row) for row in unpriced],
    }


# ---- Sync worker and CLI ----


def get_cursor(conn):
    return get_setting(conn, "cpamp_cursor")


def initialize_cursor(conn, cursor, models):
    """Persist the first cursor and initial model catalogue atomically."""
    with transaction(conn):
        for row in models:
            pricing.touch_model(conn, row["model"], row["last_ms"], row["calls"])
        set_setting(conn, "cpamp_cursor", cursor)


def normalize_tokens(row):
    """Return uncached input, cache read/write, output, reasoning and total."""
    output = _int(row["output_tokens"])
    reasoning = _int(row["reasoning_tokens"])
    if row["normalized_uncached_input_tokens"] is not None:
        uncached = _int(row["normalized_uncached_input_tokens"])
        cache_read = _int(row["normalized_cache_read_tokens"])
        cache_write = _int(row["normalized_cache_creation_tokens"])
    else:
        cache_read = max(_int(row["cache_read_tokens"]), _int(row["cached_tokens"]))
        cache_write = _int(row["cache_creation_tokens"])
        uncached = max(_int(row["input_tokens"]) - cache_read - cache_write, 0)
    total = _int(row["total_tokens"]) or (uncached + cache_read + cache_write + output)
    return uncached, cache_read, cache_write, output, reasoning, total


def apply_batch(conn, rows, keys, book, bill_failed, last_event_at=None):
    """Commit one ingestion batch; return (inserted_count, last_event_at).

    Call without an active transaction. Deduplication, balance/key updates, model
    discovery and the source cursor commit or roll back together.
    """
    billed = 0
    models = {}
    last_event_at = last_event_at or 0
    with transaction(conn):
        for row in rows:
            model = (row["model"] or row["requested_model"] or "").strip() or "unknown"
            ts = int(row["timestamp_ms"] or 0)
            last_event_at = max(last_event_at, ts)
            entry = models.setdefault(model, [0, 0])
            entry[0] = max(entry[0], ts)
            entry[1] += 1
            owner = keys.get((row["api_key_hash"] or "").strip().lower())
            if owner is None:
                continue
            key_id, user_id, key_created_at = owner
            if ts and ts < key_created_at - KEY_CLOCK_SKEW_MS:
                continue
            uncached, cache_read, cache_write, output, reasoning, total = normalize_tokens(row)
            failed = 1 if row["failed"] else 0
            price, source = book.resolve(model)
            cost = 0
            if price is not None and (bill_failed or not failed):
                cost = price.cost_micro(uncached, cache_read, cache_write, output)
            inserted = conn.execute(
                "INSERT OR IGNORE INTO usage_logs (event_hash, source_id, user_id, key_id, ts, "
                "model, endpoint, input_tokens, cache_read_tokens, cache_write_tokens, "
                "output_tokens, reasoning_tokens, total_tokens, cost_micro, failed, latency_ms, "
                "stream, price_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["event_hash"],
                    row["id"],
                    user_id,
                    key_id,
                    ts,
                    model,
                    row["endpoint"] or row["path"],
                    uncached,
                    cache_read,
                    cache_write,
                    output,
                    reasoning,
                    total,
                    cost,
                    failed,
                    row["latency_ms"],
                    None if row["stream"] is None else int(bool(row["stream"])),
                    source,
                ),
            ).rowcount
            if inserted != 1:
                continue
            billed += 1
            if cost:
                billing.charge_usage(conn, user_id, cost)
            api_keys.record_usage(conn, key_id, cost, ts)
        for model, (last_ms, calls) in models.items():
            pricing.touch_model(conn, model, last_ms, calls)
        set_setting(conn, "cpamp_cursor", rows[-1]["id"])
    return billed, last_event_at or None


def _int(value):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0
