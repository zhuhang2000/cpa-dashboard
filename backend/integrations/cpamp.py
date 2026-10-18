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
    """Read official USD prices per million tokens as ordinary dictionaries."""
    prices = {}
    if conn is None:
        return prices
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(model_prices)")}
        if not {"model", "prompt_per_1m", "completion_per_1m"} <= columns:
            return prices
        wanted = [
            "cache_per_1m",
            "cache_read_per_1m",
            "cache_creation_per_1m",
            "cache_read_configured",
            "cache_creation_configured",
        ]
        select = ["model", "prompt_per_1m", "completion_per_1m"] + [
            c if c in columns else "0 AS " + c for c in wanted
        ]
        for row in conn.execute("SELECT %s FROM model_prices" % ", ".join(select)):
            model, prompt, completion, cache, cache_read, cache_creation, cr_set, cc_set = row
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
            prices[model] = {
                "input": float(prompt),
                "output": float(completion or 0),
                "cache_read": float(read_price),
                "cache_write": float(write_price),
            }
    except Exception:
        return {}
    return prices
