"""API key lifecycle, availability rules and persistence."""

from core.constants import KeyState, KeyStatus, UserStatus
from core.db import now_ms, transaction
from core.errors import ApiError
from core.security import new_api_key, sha256_hex
from services.billing import parse_money, to_micro

NAME_MAX = 32
DEFAULT_NAME = "默认密钥"


def min_balance_micro(cfg):
    return to_micro(cfg.get("min_balance_to_call") or 0)


def max_keys(cfg):
    return int(cfg.get("max_keys_per_user") or 10)


def key_prefix(cfg):
    return cfg.get("key_prefix") or "sk-"


def hash_key(key):
    """Match CPA Manager Plus' usage_events.api_key_hash."""
    return sha256_hex(key)


def state(key_row, user_row, min_balance, now):
    """Shared availability rule for user responses and CPA synchronization."""
    if key_row["status"] != KeyStatus.ACTIVE:
        return key_row["status"]
    if key_row["expires_at"] and key_row["expires_at"] <= now:
        return KeyState.EXPIRED
    if key_row["quota_micro"] is not None and key_row["used_micro"] >= key_row["quota_micro"]:
        return KeyState.EXHAUSTED
    if user_row["balance_micro"] <= min_balance or user_row["status"] != UserStatus.ACTIVE:
        return KeyState.SUSPENDED
    return KeyStatus.ACTIVE


def desired_and_managed(conn, cfg):
    min_balance = min_balance_micro(cfg)
    now = now_ms()
    users = {row["id"]: row for row in conn.execute("SELECT id, balance_micro, status FROM users")}
    desired, managed = set(), set()
    for row in conn.execute("SELECT * FROM api_keys"):
        managed.add(row["key"])
        user = users.get(row["user_id"])
        if user is not None and state(row, user, min_balance, now) == KeyStatus.ACTIVE:
            desired.add(row["key"])
    return desired, managed


def count_live(conn, user_id):
    return conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE user_id = ? AND status != ?",
        (user_id, KeyStatus.DELETED),
    ).fetchone()[0]


def live_counts(conn, user_ids):
    if not user_ids:
        return {}
    rows = conn.execute(
        "SELECT user_id, COUNT(*) FROM api_keys WHERE status != ? AND user_id IN (%s) "
        "GROUP BY user_id" % ", ".join("?" * len(user_ids)),
        [KeyStatus.DELETED] + list(user_ids),
    )
    return {row[0]: row[1] for row in rows}


def active_count(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM api_keys WHERE status = ?", (KeyStatus.ACTIVE,)
    ).fetchone()[0]


def list_for_user(conn, user_id):
    return conn.execute(
        "SELECT * FROM api_keys WHERE user_id = ? AND status != ? ORDER BY id DESC",
        (user_id, KeyStatus.DELETED),
    ).fetchall()


def get_owned(conn, user_id, key_id):
    row = conn.execute(
        "SELECT * FROM api_keys WHERE id = ? AND user_id = ? AND status != ?",
        (key_id, user_id, KeyStatus.DELETED),
    ).fetchone()
    if row is None:
        raise ApiError(404, "密钥不存在")
    return row


def _get(conn, key_id):
    return conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()


def parse_name(value, default=None):
    name = str(value or "").strip() or default
    if not name or len(name) > NAME_MAX:
        raise ApiError(400, "名称需为 1-%d 个字符" % NAME_MAX)
    return name


def parse_quota(value):
    if value in (None, "", 0, "0"):
        return None
    return parse_money(value, "额度上限", minimum=0)


def parse_optional_ts(value, field):
    if value in (None, "", 0):
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "%s格式不正确" % field)
    if ts <= now_ms():
        raise ApiError(400, "%s必须是将来的时间" % field)
    return ts


def create(conn, cfg, user_id, data):
    name = parse_name(data.get("name"), DEFAULT_NAME)
    quota = parse_quota(data.get("quota"))
    expires_at = parse_optional_ts(data.get("expires_at"), "过期时间")
    limit = max_keys(cfg)
    with transaction(conn):
        if count_live(conn, user_id) >= limit:
            raise ApiError(400, "每个账号最多创建 %d 个密钥" % limit)
        key = new_api_key(key_prefix(cfg))
        key_id = conn.execute(
            "INSERT INTO api_keys (user_id, name, key, key_hash, quota_micro, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, key, hash_key(key), quota, expires_at, now_ms()),
        ).lastrowid
    return _get(conn, key_id)


def update(conn, key_row, data):
    fields, args = [], []
    if "name" in data:
        fields.append("name = ?")
        args.append(parse_name(data.get("name")))
    if "status" in data:
        if data["status"] not in KeyStatus.SETTABLE:
            raise ApiError(400, "状态不正确")
        fields.append("status = ?")
        args.append(data["status"])
    if "quota" in data:
        fields.append("quota_micro = ?")
        args.append(parse_quota(data.get("quota")))
    if "expires_at" in data:
        fields.append("expires_at = ?")
        args.append(parse_optional_ts(data.get("expires_at"), "过期时间"))
    if fields:
        conn.execute(
            "UPDATE api_keys SET %s WHERE id = ?" % ", ".join(fields), args + [key_row["id"]]
        )
    return _get(conn, key_row["id"])


def soft_delete(conn, key_row):
    conn.execute(
        "UPDATE api_keys SET status = ?, deleted_at = ? WHERE id = ?",
        (KeyStatus.DELETED, now_ms(), key_row["id"]),
    )


def billing_owners(conn):
    return {
        row["key_hash"]: (row["id"], row["user_id"], row["created_at"])
        for row in conn.execute("SELECT id, user_id, key_hash, created_at FROM api_keys")
    }


def first_created_at(conn):
    return conn.execute("SELECT MIN(created_at) FROM api_keys").fetchone()[0]


def record_usage(conn, key_id, cost_micro, ts):
    """Count a recorded request inside the usage importer's transaction."""
    conn.execute(
        "UPDATE api_keys SET used_micro = used_micro + ?, request_count = request_count + 1, "
        "last_used_at = MAX(COALESCE(last_used_at, 0), ?) WHERE id = ?",
        (cost_micro, ts, key_id),
    )
