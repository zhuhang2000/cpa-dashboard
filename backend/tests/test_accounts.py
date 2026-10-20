"""Account and key behavior exercised without HTTP or external services."""

import sqlite3

import pytest

from core.constants import Role, UserStatus
from core.db import connect, init_db
from core.errors import ApiError
from core.security import RateLimiter, sha256_hex, verify_password
from services import accounts, api_keys

NOW = 1700000000000
DAY_MS = 86400000


@pytest.fixture
def account_db(tmp_path, monkeypatch):
    path = str(tmp_path / "accounts.sqlite")
    init_db(path)
    conn = connect(path)
    monkeypatch.setattr(accounts, "now_ms", lambda: NOW)
    try:
        yield conn
    finally:
        conn.close()


def add_user(conn, username, *, role=Role.USER):
    user_id = conn.execute(
        "INSERT INTO users (username, password_hash, role, balance_micro, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (username, "unused-test-hash", role, 1000000, NOW),
    ).lastrowid
    return accounts.get(conn, user_id)


def test_session_expiration_and_sliding_renewal(account_db):
    conn = account_db
    user = add_user(conn, "alice")
    token, age = accounts.start_session(conn, user["id"], "127.0.0.1", 7, "test-browser")
    authenticated, renewal = accounts.authenticate_session(conn, token, 7)
    assert authenticated["id"] == user["id"]
    assert renewal is None
    assert age == 7 * 86400
    assert conn.execute("SELECT user_agent FROM sessions").fetchone()[0] == "test-browser"

    token_hash = sha256_hex(token)
    conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (NOW + DAY_MS, token_hash)
    )
    authenticated, renewal = accounts.authenticate_session(conn, token, 7)
    assert authenticated["id"] == user["id"]
    assert renewal == age
    assert (
        conn.execute(
            "SELECT expires_at FROM sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()[0]
        == NOW + 7 * DAY_MS
    )

    conn.execute("UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (NOW, token_hash))
    assert accounts.authenticate_session(conn, token, 7) == (None, None)
    assert accounts.authenticate_session(conn, "unknown-token", 7) == (None, None)


def test_banning_user_revokes_sessions_and_blocks_authentication(account_db):
    conn = account_db
    user = add_user(conn, "alice")
    admin = add_user(conn, "operator", role=Role.ADMIN)
    first, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)
    accounts.start_session(conn, user["id"], "127.0.0.2", 7)

    changed = accounts.update_user(conn, user["id"], {"status": UserStatus.BANNED}, admin["id"])
    assert changed["status"] == UserStatus.BANNED
    assert (
        conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()[0]
        == 0
    )
    assert accounts.authenticate_session(conn, first, 7) == (None, None)

    # A stale session row must not bypass the account's banned status.
    stale, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)
    assert accounts.authenticate_session(conn, stale, 7) == (None, None)


def test_logout_revokes_only_the_selected_session(account_db):
    conn = account_db
    user = add_user(conn, "alice")
    first, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)
    second, _ = accounts.start_session(conn, user["id"], "127.0.0.2", 7)
    accounts.logout(conn, sha256_hex(first))
    assert accounts.authenticate_session(conn, first, 7) == (None, None)
    assert accounts.authenticate_session(conn, second, 7)[0]["id"] == user["id"]
    accounts.logout(conn, None)


def test_users_cannot_read_or_change_another_users_key(account_db):
    conn = account_db
    alice = add_user(conn, "alice")
    bob = add_user(conn, "bob")
    key = api_keys.create(conn, {}, alice["id"], {"name": "Alice's key"})

    with pytest.raises(ApiError) as exc:
        api_keys.get_owned(conn, bob["id"], key["id"])
    assert exc.value.status == 404
    assert api_keys.list_for_user(conn, bob["id"]) == []
    assert api_keys.get_owned(conn, alice["id"], key["id"])["name"] == "Alice's key"

    api_keys.soft_delete(conn, key)
    with pytest.raises(ApiError) as exc:
        api_keys.get_owned(conn, alice["id"], key["id"])
    assert exc.value.status == 404
    desired, managed = api_keys.desired_and_managed(conn, {})
    assert key["key"] not in desired
    assert key["key"] in managed


def test_cli_admin_creation_promotion_and_password_reset(account_db):
    conn = account_db
    user, created = accounts.create_admin(conn, "alice", "initial-password")
    assert created is True
    assert user["role"] == Role.ADMIN
    assert verify_password("initial-password", user["password_hash"])
    first, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)
    accounts.start_session(conn, user["id"], "127.0.0.2", 7)

    conn.execute(
        "UPDATE users SET role = ?, status = ? WHERE id = ?",
        (Role.USER, UserStatus.BANNED, user["id"]),
    )
    promoted, created = accounts.create_admin(conn, "alice")
    assert created is False
    assert promoted["role"] == Role.ADMIN
    assert promoted["status"] == UserStatus.ACTIVE
    assert promoted["password_hash"] == user["password_hash"]

    accounts.reset_password(conn, user["id"], "replacement-password")
    updated = accounts.find_by_username(conn, "ALICE")
    assert verify_password("replacement-password", updated["password_hash"])
    assert not verify_password("initial-password", updated["password_hash"])
    assert (
        conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()[0]
        == 0
    )
    assert accounts.authenticate_session(conn, first, 7) == (None, None)


def test_password_change_keeps_current_session(account_db):
    conn = account_db
    user, _ = accounts.create_admin(conn, "alice", "initial-password")
    current, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)
    other, _ = accounts.start_session(conn, user["id"], "127.0.0.2", 7)

    accounts.change_password(
        conn,
        user,
        {
            "old_password": "initial-password",
            "new_password": "replacement-password",
        },
        sha256_hex(current),
    )
    assert accounts.authenticate_session(conn, current, 7)[0]["id"] == user["id"]
    assert accounts.authenticate_session(conn, other, 7) == (None, None)


def test_admin_password_reset_revokes_sessions_and_rejects_self(account_db):
    conn = account_db
    admin = add_user(conn, "root", role=Role.ADMIN)
    user = add_user(conn, "alice")
    session, _ = accounts.start_session(conn, user["id"], "127.0.0.1", 7)

    with pytest.raises(ApiError, match="至少 8 位"):
        accounts.admin_reset_password(conn, user["id"], {"password": "short"}, admin["id"])
    with pytest.raises(ApiError, match="个人设置"):
        accounts.admin_reset_password(conn, admin["id"], {"password": "replacement"}, admin["id"])
    with pytest.raises(ApiError, match="用户不存在"):
        accounts.admin_reset_password(conn, 9999, {"password": "replacement"}, admin["id"])

    accounts.admin_reset_password(conn, user["id"], {"password": "replacement"}, admin["id"])
    assert verify_password("replacement", accounts.get(conn, user["id"])["password_hash"])
    assert accounts.authenticate_session(conn, session, 7) == (None, None)


def test_registration_rolls_back_account_and_bonus_when_session_creation_fails(account_db):
    conn = account_db
    conn.execute(
        "CREATE TRIGGER reject_session BEFORE INSERT ON sessions "
        "BEGIN SELECT RAISE(ABORT, 'session write failed'); END"
    )

    with pytest.raises(sqlite3.IntegrityError, match="session write failed"):
        accounts.register(
            conn,
            {"username": "alice", "password": "valid-password"},
            "127.0.0.1",
            RateLimiter(),
            True,
            5,
            7,
        )

    assert accounts.find_by_username(conn, "alice") is None
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
