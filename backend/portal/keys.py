"""API keys: validation, lifecycle and the rule that decides whether a key is usable.

state() is the single source of truth: the state users see in the console and
the set of keys the sync worker pushes to CLIProxyAPI are both derived from it.
"""
from .billing import to_micro
from .common import money, parse_money, parse_optional_ts
from .constants import KeyState, KeyStatus, UserStatus
from .db import now_ms, transaction
from .security import new_api_key, sha256_hex
from .web import ApiError

NAME_MAX = 32
DEFAULT_NAME = "默认密钥"


# -- config --------------------------------------------------------------------------
def min_balance_micro(app):
    """Keys stop working once the owner's balance is at or below this."""
    return to_micro(app.cfg.get("min_balance_to_call") or 0)


def max_keys(app):
    return int(app.cfg.get("max_keys_per_user") or 10)


def _prefix(app):
    return app.cfg.get("key_prefix") or "sk-"


# -- secrets -------------------------------------------------------------------------
def hash_key(key):
    """Must equal CPA Manager Plus' usage_events.api_key_hash, which billing matches on."""
    return sha256_hex(key)


def mask(key, prefix):
    head = len(prefix) + 4
    return key[:head] + "…" + key[-4:]


# -- state ---------------------------------------------------------------------------
def state(key_row, user_row, min_balance, now):
    """Why a key can or cannot be used right now; only ACTIVE keys are synced to CPA."""
    if key_row["status"] != KeyStatus.ACTIVE:
        return key_row["status"]  # disabled / deleted
    if key_row["expires_at"] and key_row["expires_at"] <= now:
        return KeyState.EXPIRED
    if key_row["quota_micro"] is not None and key_row["used_micro"] >= key_row["quota_micro"]:
        return KeyState.EXHAUSTED
    if user_row["balance_micro"] <= min_balance or user_row["status"] != UserStatus.ACTIVE:
        return KeyState.SUSPENDED
    return KeyStatus.ACTIVE


def desired_and_managed(conn, app):
    """Return (keys that may be used now, every key the portal has issued).

    `managed` deliberately includes deleted keys: the sync removes managed keys
    that are not desired, which is how a deleted key leaves CPA.
    """
    min_balance = min_balance_micro(app)
    now = now_ms()
    users = {row["id"]: row for row in conn.execute("SELECT id, balance_micro, status FROM users")}
    desired, managed = set(), set()
    for row in conn.execute("SELECT * FROM api_keys"):
        managed.add(row["key"])
        user = users.get(row["user_id"])
        if user is not None and state(row, user, min_balance, now) == KeyStatus.ACTIVE:
            desired.add(row["key"])
    return desired, managed


# -- reads ---------------------------------------------------------------------------
def count_live(conn, user_id):
    return conn.execute("SELECT COUNT(*) FROM api_keys WHERE user_id = ? AND status != ?",
                        (user_id, KeyStatus.DELETED)).fetchone()[0]


def live_counts(conn, user_ids):
    """{user_id: number of non-deleted keys} for a page of users."""
    if not user_ids:
        return {}
    rows = conn.execute(
        "SELECT user_id, COUNT(*) FROM api_keys WHERE status != ? AND user_id IN (%s) "
        "GROUP BY user_id" % ", ".join("?" * len(user_ids)),
        [KeyStatus.DELETED] + list(user_ids),
    )
    return {row[0]: row[1] for row in rows}


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


# -- validation & writes (callers trigger the sync worker afterwards) ----------------
def parse_name(value, default=None):
    name = str(value or "").strip() or default
    if not name or len(name) > NAME_MAX:
        raise ApiError(400, "名称需为 1-%d 个字符" % NAME_MAX)
    return name


def parse_quota(value):
    """Spending cap in micro-units; empty or 0 means unlimited."""
    if value in (None, "", 0, "0"):
        return None
    return parse_money(value, "额度上限", minimum=0)


def create(conn, app, user_id, data):
    """Validate `data` and issue a key. Returns the stored row, plaintext key included."""
    name = parse_name(data.get("name"), DEFAULT_NAME)
    quota = parse_quota(data.get("quota"))
    expires_at = parse_optional_ts(data.get("expires_at"), "过期时间")
    limit = max_keys(app)
    with transaction(conn):
        if count_live(conn, user_id) >= limit:
            raise ApiError(400, "每个账号最多创建 %d 个密钥" % limit)
        key = new_api_key(_prefix(app))
        key_id = conn.execute(
            "INSERT INTO api_keys (user_id, name, key, key_hash, quota_micro, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, key, hash_key(key), quota, expires_at, now_ms()),
        ).lastrowid
    return _get(conn, key_id)


def update(conn, key_row, data):
    """Apply the fields present in `data` (name/status/quota/expires_at). Returns the new row."""
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
        conn.execute("UPDATE api_keys SET %s WHERE id = ?" % ", ".join(fields),
                     args + [key_row["id"]])
    return _get(conn, key_row["id"])


def soft_delete(conn, key_row):
    """Keep the row for usage history; the next sync removes the key from CPA."""
    conn.execute("UPDATE api_keys SET status = ?, deleted_at = ? WHERE id = ?",
                 (KeyStatus.DELETED, now_ms(), key_row["id"]))


# -- output --------------------------------------------------------------------------
def to_public(app, row, user):
    return {
        "id": row["id"],
        "name": row["name"],
        "masked": mask(row["key"], _prefix(app)),
        "status": row["status"],
        "state": state(row, user, min_balance_micro(app), now_ms()),
        "quota": None if row["quota_micro"] is None else money(row["quota_micro"]),
        "used": money(row["used_micro"]),
        "request_count": row["request_count"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "last_used_at": row["last_used_at"],
    }
