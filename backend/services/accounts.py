"""Accounts and login sessions shared by the HTTP API and command line."""

import re
import secrets

from core.constants import Role, TxType, UserStatus
from core.db import now_ms, transaction
from core.errors import ApiError
from core.security import hash_password, new_session_token, sha256_hex, verify_password
from services.billing import apply_credit, to_micro

DAY_MS = 86400000
MAX_BATCH_USERS = 100  # the largest user list page
USER_SORTS = {
    "created": "u.id",
    "last_used": "last_used_at",
    "last_login": "u.last_login_at",
    "balance": "u.balance_micro",
    "recharge": "u.total_recharge_micro",
    "spent": "u.total_spent_micro",
}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,253}\.[^@\s.]{2,}$")
_DUMMY_HASH = []


def validate_username(username):
    if not USERNAME_RE.match(username):
        raise ApiError(400, "用户名需为 3-32 位字母、数字、下划线或短横线")


def validate_password(password):
    if len(password) < 8:
        raise ApiError(400, "密码至少 8 位")
    if len(password) > 128:
        raise ApiError(400, "密码过长")


def _dummy_hash():
    if not _DUMMY_HASH:
        _DUMMY_HASH.append(hash_password(secrets.token_hex(8)))
    return _DUMMY_HASH[0]


def get(conn, user_id):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise ApiError(404, "用户不存在")
    return row


def find_by_username(conn, username):
    return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def start_session(conn, user_id, ip, session_days, user_agent=""):
    """Create a session in the caller's transaction and return (token, max_age)."""
    token = new_session_token()
    lifetime = int(session_days or 7) * DAY_MS
    now = now_ms()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at, ip, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (sha256_hex(token), user_id, now, now + lifetime, ip, (user_agent or "")[:200]),
    )
    return token, lifetime // 1000


def authenticate_session(conn, token, session_days):
    """Return (active user, renewed cookie lifetime), without handling HTTP cookies."""
    if not token:
        return None, None
    token_hash = sha256_hex(token)
    row = conn.execute(
        "SELECT u.*, s.expires_at AS session_expires_at FROM sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
        (token_hash,),
    ).fetchone()
    now = now_ms()
    if row is None or row["session_expires_at"] <= now or row["status"] != UserStatus.ACTIVE:
        return None, None
    lifetime = int(session_days or 7) * DAY_MS
    if row["session_expires_at"] - now < lifetime // 2:
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (now + lifetime, token_hash)
        )
        return row, lifetime // 1000
    return row, None


def logout(conn, token_hash):
    if token_hash:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def register(conn, data, ip, limiter, allow_register, signup_bonus, session_days, user_agent=""):
    if not allow_register:
        raise ApiError(403, "当前未开放注册")
    username = str(data.get("username") or "").strip()
    email = str(data.get("email") or "").strip() or None
    password = str(data.get("password") or "")
    validate_username(username)
    if email is not None and not EMAIL_RE.match(email):
        raise ApiError(400, "邮箱格式不正确")
    validate_password(password)
    if not limiter.allow("register:" + ip, 10, 3600):
        raise ApiError(429, "注册过于频繁，请稍后再试")
    password_hash = hash_password(password)
    bonus = to_micro(signup_bonus or 0)
    with transaction(conn):
        if find_by_username(conn, username):
            raise ApiError(409, "用户名已被占用")
        if email and conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise ApiError(409, "该邮箱已注册")
        user_id = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at, last_login_at, "
            "last_login_ip) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, password_hash, now_ms(), now_ms(), ip),
        ).lastrowid
        if bonus > 0:
            apply_credit(conn, user_id, bonus, TxType.BONUS, note="注册赠送")
        token, max_age = start_session(conn, user_id, ip, session_days, user_agent)
    return get(conn, user_id), token, max_age


def login(conn, data, ip, limiter, session_days, user_agent=""):
    account = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if not account or not password:
        raise ApiError(400, "请输入用户名和密码")
    ip_key = "login-ip:" + ip
    account_key = "login-account:" + account.lower()
    if limiter.count(ip_key, 600) >= 20 or limiter.count(account_key, 600) >= 10:
        raise ApiError(429, "登录失败次数过多，请 10 分钟后再试")
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?", (account, account)
    ).fetchone()
    valid = verify_password(password, row["password_hash"] if row else _dummy_hash())
    if row is None or not valid:
        limiter.add(ip_key)
        limiter.add(account_key)
        raise ApiError(401, "用户名或密码错误")
    if row["status"] != UserStatus.ACTIVE:
        raise ApiError(403, "账号已被禁用，请联系管理员")
    limiter.reset(account_key)
    with transaction(conn):
        conn.execute(
            "UPDATE users SET last_login_at = ?, last_login_ip = ? WHERE id = ?",
            (now_ms(), ip, row["id"]),
        )
        token, max_age = start_session(conn, row["id"], ip, session_days, user_agent)
    return get(conn, row["id"]), token, max_age


def update_profile(conn, user_id, data):
    email = str(data.get("email") or "").strip() or None
    if email is not None and not EMAIL_RE.match(email):
        raise ApiError(400, "邮箱格式不正确")
    with transaction(conn):
        if (
            email
            and conn.execute(
                "SELECT 1 FROM users WHERE email = ? AND id != ?", (email, user_id)
            ).fetchone()
        ):
            raise ApiError(409, "该邮箱已被其他账号使用")
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    return get(conn, user_id)


def change_password(conn, user, data, keep_session):
    old = str(data.get("old_password") or "")
    new = str(data.get("new_password") or "")
    if not verify_password(old, user["password_hash"]):
        raise ApiError(400, "当前密码不正确")
    validate_password(new)
    password_hash = hash_password(new)
    with transaction(conn):
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user["id"]))
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user["id"], keep_session)
        )


def search(conn, q, limit, offset, archived=False, sort="created", desc=True):
    """Archived (inactive) accounts are listed apart from the main user list.

    Rows carry last_used_at, the latest call made with any of the user's keys. Missing
    times sort as the oldest, so never-used accounts lead an ascending order.
    """
    where = "u.archived_at IS NOT NULL" if archived else "u.archived_at IS NULL"
    args = []
    if q:
        where += " AND (u.username LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')"
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        args = [pattern, pattern]
    order = "%s %s, u.id DESC" % (USER_SORTS.get(sort, "u.id"), "DESC" if desc else "ASC")
    total = conn.execute("SELECT COUNT(*) FROM users u WHERE " + where, args).fetchone()[0]
    rows = conn.execute(
        "SELECT u.*, (SELECT MAX(k.last_used_at) FROM api_keys k WHERE k.user_id = u.id) "
        "AS last_used_at FROM users u WHERE " + where + " ORDER BY " + order + " LIMIT ? OFFSET ?",
        args + [limit, offset],
    ).fetchall()
    return total, rows


def set_archived(conn, user_ids, archived):
    """Move accounts in or out of the inactive list; sign-in and keys are unaffected."""
    if not isinstance(archived, bool):
        raise ApiError(400, "不活跃标记不正确")
    if (
        not isinstance(user_ids, list)
        or not 1 <= len(user_ids) <= MAX_BATCH_USERS
        or not all(type(user_id) is int for user_id in user_ids)
    ):
        raise ApiError(400, "请选择 1-%d 位用户" % MAX_BATCH_USERS)
    return conn.execute(
        "UPDATE users SET archived_at = CASE WHEN ? THEN COALESCE(archived_at, ?) END "
        "WHERE id IN (%s)" % ", ".join("?" * len(user_ids)),
        [archived, now_ms()] + user_ids,
    ).rowcount


def set_status(conn, user_id, status, operator_id):
    """Ban or re-enable an account; a ban also signs it out everywhere."""
    row = get(conn, user_id)
    if status not in UserStatus.ALL:
        raise ApiError(400, "状态不正确")
    if row["id"] == operator_id and status != UserStatus.ACTIVE:
        raise ApiError(400, "不能禁用自己的账号")
    with transaction(conn):
        conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, row["id"]))
        if status == UserStatus.BANNED:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
    return get(conn, row["id"])


def set_role(conn, user_id, role, operator_id):
    """Grant or revoke administrator rights."""
    row = get(conn, user_id)
    if role not in Role.ALL:
        raise ApiError(400, "角色不正确")
    if row["id"] == operator_id and role != Role.ADMIN:
        raise ApiError(400, "不能取消自己的管理员身份")
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, row["id"]))
    return get(conn, row["id"])


def create_admin(conn, username, password=None):
    """Return (user, created); an existing account is promoted without a password change."""
    validate_username(username)
    row = find_by_username(conn, username)
    if row:
        conn.execute(
            "UPDATE users SET role = ?, status = ? WHERE id = ?",
            (Role.ADMIN, UserStatus.ACTIVE, row["id"]),
        )
        return get(conn, row["id"]), False
    if password is None:
        raise ValueError("password is required for a new administrator")
    user_id = conn.execute(
        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
        (username, hash_password(password), Role.ADMIN, now_ms()),
    ).lastrowid
    return get(conn, user_id), True


def reset_password(conn, user_id, password):
    """CLI reset: retain its existing password policy and revoke every session."""
    with transaction(conn):
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id)
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def admin_reset_password(conn, user_id, data, operator_id):
    """Administrator reset for a forgotten password; the user must sign in again."""
    row = get(conn, user_id)
    if row["id"] == operator_id:
        raise ApiError(400, "请在个人设置中修改自己的密码")
    password = str(data.get("password") or "")
    validate_password(password)
    reset_password(conn, row["id"], password)


def overview_counts(conn, today):
    return {
        "total": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "today": conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (today,)
        ).fetchone()[0],
        "balance_total_micro": conn.execute("SELECT SUM(balance_micro) FROM users").fetchone()[0]
        or 0,
    }
