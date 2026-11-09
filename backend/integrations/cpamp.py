"""Read-only access to CPA Manager Plus' SQLite database.

External schema differences are handled here. Results contain plain data so
this adapter does not depend on portal services or their pricing classes.
"""

import os
import pathlib
import sqlite3

EVENT_COLUMNS = [
    "id",
    "event_hash",
    "timestamp_ms",
    "model",
    "requested_model",
    "endpoint",
    "path",
    "api_key_hash",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cached_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "normalized_uncached_input_tokens",
    "normalized_cache_read_tokens",
    "normalized_cache_creation_tokens",
    "total_tokens",
    "failed",
    "latency_ms",
    "stream",
]
REQUIRED_COLUMNS = {"id", "event_hash", "timestamp_ms", "model", "api_key_hash"}
# Optional price columns, shared by model_prices and model_price_context_tiers.
PRICE_COLUMNS = [
    "cache_per_1m",
    "cache_read_per_1m",
    "cache_creation_per_1m",
    "cache_read_configured",
    "cache_creation_configured",
]


def open_database(path):
    """Open an existing external database without permitting writes."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError("未找到 CPA Manager Plus 数据库: %s" % path)
    uri = pathlib.Path(path).absolute().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = 1")
    return conn


def usage_columns(conn):
    """Validate the usage schema and return its available columns."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(usage_events)")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError("usage_events 缺少字段: %s" % ", ".join(sorted(missing)))
    return columns


def read_events(conn, cursor, batch_size, columns):
    select = ", ".join(c if c in columns else "NULL AS " + c for c in EVENT_COLUMNS)
    return [
        dict(row)
        for row in conn.execute(
            "SELECT %s FROM usage_events WHERE id > ? ORDER BY id LIMIT ?" % select,
            (cursor, batch_size),
        )
    ]


def initial_cursor(conn, before_ms=None):
    if before_ms is None:
        return conn.execute("SELECT COALESCE(MAX(id), 0) FROM usage_events").fetchone()[0]
    return conn.execute(
        "SELECT COALESCE(MAX(id), 0) FROM usage_events WHERE timestamp_ms < ?",
        (before_ms,),
    ).fetchone()[0]


def recent_models(conn, cursor):
    return [
        dict(row)
        for row in conn.execute(
            "SELECT model, MAX(timestamp_ms) AS last_ms, COUNT(*) AS calls FROM usage_events "
            "WHERE id > ? GROUP BY model",
            (max(cursor - 50000, 0),),
        )
    ]


def load_prices(conn):
    """Read official USD prices per million tokens as ordinary dictionaries.

    Each model carries its long-context `tiers` (ascending `threshold`): a request whose input,
    cache included, exceeds a threshold is priced wholly at that tier, as CPA Manager Plus does.
    """
    prices = {}
    if conn is None:
        return prices
    try:
        select = _price_select(conn, "model_prices", ["model"])
        if select is None:
            return prices
        for model, *values in conn.execute("SELECT %s FROM model_prices" % select):
            prices[model] = {**_price(*values), "tiers": []}
    except Exception:
        return {}
    # A CPA Manager Plus without the tier table bills every request at the base price.
    try:
        select = _price_select(conn, "model_price_context_tiers", ["model", "threshold_tokens"])
        sql = "SELECT %s FROM model_price_context_tiers ORDER BY threshold_tokens" % select
        tiers = conn.execute(sql).fetchall() if select else []
    except Exception:
        tiers = []
    for model, threshold, *values in tiers:
        if model in prices:
            prices[model]["tiers"].append({"threshold": int(threshold), **_price(*values)})
    return prices


def _price_select(conn, table, keys):
    """Return the select list of a price table, or None when its required columns are missing."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)}
    if not set(keys) | {"prompt_per_1m", "completion_per_1m"} <= columns:
        return None
    optional = [c if c in columns else "0 AS " + c for c in PRICE_COLUMNS]
    return ", ".join(keys + ["prompt_per_1m", "completion_per_1m"] + optional)


def _price(prompt, completion, cache, cache_read, cache_creation, cr_set, cc_set):
    prompt = prompt or 0
    if cr_set or (cache_read or 0) > 0:
        read_price = cache_read or 0
    elif (cache or 0) > 0:
        read_price = cache
    else:
        read_price = prompt * 0.1
    write_price = cache_creation if (cc_set or (cache_creation or 0) > 0) else prompt * 1.25
    if write_price is None:
        write_price = float(prompt) * 1.25
    return {
        "input": float(prompt),
        "output": float(completion or 0),
        "cache_read": float(read_price),
        "cache_write": float(write_price),
    }
