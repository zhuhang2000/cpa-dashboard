"""SQLite storage for the portal (users, keys, billing). Python 3.10+ / SQLite 3.22+."""

import contextlib
import json
import sqlite3
import time

SCHEMA_V1 = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    email TEXT COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    balance_micro INTEGER NOT NULL DEFAULT 0,
    total_recharge_micro INTEGER NOT NULL DEFAULT 0,
    total_spent_micro INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    last_login_at INTEGER,
    last_login_ip TEXT
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    ip TEXT,
    user_agent TEXT
);
CREATE INDEX idx_sessions_user ON sessions(user_id);

CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    key TEXT NOT NULL UNIQUE,
    key_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    quota_micro INTEGER,
    used_micro INTEGER NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    expires_at INTEGER,
    created_at INTEGER NOT NULL,
    last_used_at INTEGER,
    deleted_at INTEGER
);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_hash TEXT NOT NULL UNIQUE,
    source_id INTEGER,
    user_id INTEGER NOT NULL,
    key_id INTEGER NOT NULL,
    ts INTEGER NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_micro INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    stream INTEGER,
    price_source TEXT
);
CREATE INDEX idx_usage_user_ts ON usage_logs(user_id, ts);
CREATE INDEX idx_usage_key_ts ON usage_logs(key_id, ts);
CREATE INDEX idx_usage_ts ON usage_logs(ts);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type TEXT NOT NULL,
    amount_micro INTEGER NOT NULL,
    balance_after_micro INTEGER NOT NULL,
    ref TEXT,
    note TEXT,
    operator_id INTEGER,
    created_at INTEGER NOT NULL
);
CREATE INDEX idx_transactions_user ON transactions(user_id, created_at);
CREATE INDEX idx_transactions_created ON transactions(created_at);

CREATE TABLE redeem_codes (
    code TEXT PRIMARY KEY,
    amount_micro INTEGER NOT NULL,
    batch TEXT,
    status TEXT NOT NULL DEFAULT 'unused',
    created_by INTEGER,
    created_at INTEGER NOT NULL,
    expires_at INTEGER,
    used_by INTEGER,
    used_at INTEGER
);
CREATE INDEX idx_redeem_codes_created ON redeem_codes(created_at);

CREATE TABLE orders (
    order_no TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    channel TEXT NOT NULL,
    pay_amount TEXT NOT NULL,
    credit_micro INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    trade_no TEXT,
    created_at INTEGER NOT NULL,
    paid_at INTEGER
);
CREATE INDEX idx_orders_user ON orders(user_id, created_at);

CREATE TABLE model_prices (
    model TEXT PRIMARY KEY,
    input_price REAL NOT NULL DEFAULT 0,
    output_price REAL NOT NULL DEFAULT 0,
    cache_read_price REAL,
    cache_write_price REAL,
    note TEXT,
    updated_at INTEGER NOT NULL
);

CREATE TABLE seen_models (
    model TEXT PRIMARY KEY,
    last_seen_ms INTEGER NOT NULL,
    calls INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
"""

SCHEMA_V2 = """
ALTER TABLE redeem_codes ADD COLUMN type TEXT NOT NULL DEFAULT 'recharge'
    CHECK (type IN ('recharge', 'gift'));
"""

SCHEMA_V3 = """
CREATE TABLE notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_by INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX idx_notices_created ON notices(created_at);
"""

SCHEMA_V4 = """
ALTER TABLE users ADD COLUMN archived_at INTEGER;
"""

MIGRATIONS = [SCHEMA_V1, SCHEMA_V2, SCHEMA_V3, SCHEMA_V4]


def now_ms():
    return int(time.time() * 1000)


def connect(path):
    conn = sqlite3.connect(path, timeout=15, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db(path):
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
            try:
                conn.executescript(
                    "BEGIN IMMEDIATE;\n%s\nPRAGMA user_version = %d;\nCOMMIT;" % (script, number)
                )
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
    finally:
        conn.close()


@contextlib.contextmanager
def transaction(conn):
    """BEGIN IMMEDIATE so balance updates never hit a lock-upgrade deadlock."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row[0])


def set_setting(conn, key, value):
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(value, ensure_ascii=False), now_ms()),
    )


def like_pattern(text):
    """Escape an SQL LIKE substring while keeping parameter binding at the caller."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
