"""Admin lookups of a user's keys, ledger and usage must stay scoped to that account."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.config import load_config
from core.constants import KeyStatus, TxType
from core.db import now_ms
from core.errors import ApiError
from core.security import hash_password
from runtime.app import Runtime, create_app
from services import accounts, api_keys, billing


@pytest.fixture
def key_portal(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "core" / ".env.example")
    cfg.update(data_dir=str(tmp_path / "data"), frontend_dir=str(tmp_path / "frontend"))
    cfg["cpamp"]["usage_db"] = ""
    runtime = Runtime(cfg)
    conn = runtime.db()
    try:
        accounts.create_admin(conn, "admin", "test-password")
        password_hash = hash_password("test-password")
        users = {}
        keys = {}
        for username in ("alice", "bob"):
            user_id = conn.execute(
                "INSERT INTO users (username, password_hash, balance_micro, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, 10000000, now_ms()),
            ).lastrowid
            users[username] = user_id
            keys[username] = dict(api_keys.create(conn, cfg, user_id, {"name": username + " key"}))
    finally:
        conn.close()
    app = create_app(runtime=runtime, start_worker=False)
    with TestClient(app) as client:
        client.headers["X-Requested-With"] = "portal"
        yield client, runtime, users, keys


def login(client, username):
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "test-password"}
    )
    assert response.status_code == 200


def test_admin_endpoints_require_admin_and_do_not_expand_user_access(key_portal):
    client, runtime, users, keys = key_portal
    path = f"/api/admin/users/{users['alice']}/keys"
    for username, expected in ((None, 401), ("alice", 403)):
        if username:
            login(client, username)
        assert client.get(path).status_code == expected
        assert client.delete(f"{path}/{keys['alice']['id']}").status_code == expected
        for detail in ("billing/transactions", "usage/logs"):
            assert client.get(f"/api/admin/users/{users['alice']}/{detail}").status_code == expected
        archive = {"ids": [users["alice"]], "archived": True}
        assert client.post("/api/admin/users/archive", json=archive).status_code == expected
    own = client.get("/api/keys").json()["items"]
    assert len(own) == 1 and "key" not in own[0]
    assert client.delete(f"/api/keys/{keys['bob']['id']}").status_code == 404
    assert client.post(f"/api/keys/{keys['bob']['id']}/reveal").status_code == 404
    assert not runtime.worker._wake.is_set()


def test_admin_lists_exact_user_keys_and_uses_owner_availability(key_portal):
    client, runtime, users, keys = key_portal
    login(client, "admin")
    conn = runtime.db()
    try:
        conn.execute("UPDATE users SET balance_micro = 0 WHERE id = ?", (users["alice"],))
        deleted = api_keys.create(conn, runtime.cfg, users["alice"], {"name": "deleted"})
        api_keys.soft_delete(conn, deleted)
    finally:
        conn.close()
    response = client.get(f"/api/admin/users/{users['alice']}/keys")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["key"] == keys["alice"]["key"]
    assert items[0]["state"] == "suspended"
    assert items[0]["request_count"] == 0 and items[0]["last_used_at"] is None
    assert client.get("/api/admin/users/99999/keys").status_code == 404
    admin_id = client.get("/api/user/me").json()["user"]["id"]
    assert client.get(f"/api/admin/users/{admin_id}/keys").json() == {"items": []}


def test_admin_delete_checks_owner_preserves_history_and_triggers_removal(key_portal):
    client, runtime, users, keys = key_portal
    login(client, "admin")
    path = f"/api/admin/users/{users['alice']}/keys"
    assert client.delete(f"{path}/{keys['bob']['id']}").status_code == 404
    assert not runtime.worker._wake.is_set()
    conn = runtime.db()
    try:
        conn.execute(
            "INSERT INTO usage_logs (event_hash, source_id, user_id, key_id, ts, model, cost_micro) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("kept-event", 1, users["alice"], keys["alice"]["id"], now_ms(), "test-model", 2500),
        )
        api_keys.record_usage(conn, keys["alice"]["id"], 2500, now_ms())
    finally:
        conn.close()
    assert client.delete(f"{path}/{keys['alice']['id']}").json() == {"ok": True}
    assert runtime.worker._wake.is_set()
    assert client.get(path).json() == {"items": []}
    listed = client.get("/api/admin/users", params={"q": "alice"}).json()["items"]
    assert listed[0]["key_count"] == 0
    assert client.delete(f"{path}/{keys['alice']['id']}").status_code == 404
    conn = runtime.db()
    try:
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (keys["alice"]["id"],)).fetchone()
        assert row["status"] == KeyStatus.DELETED and row["deleted_at"] is not None
        assert row["used_micro"] == 2500 and row["request_count"] == 1
        assert conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0] == 1
        assert accounts.get(conn, users["alice"])["balance_micro"] == 10000000
        desired, managed = api_keys.desired_and_managed(conn, runtime.cfg)
        assert keys["alice"]["key"] not in desired and keys["alice"]["key"] in managed
        assert keys["bob"]["key"] in desired
    finally:
        conn.close()

    class FakeCPA:
        configured = True

        def __init__(self):
            self.keys = [keys["alice"]["key"], keys["bob"]["key"], "external-key"]

        def list_api_keys(self):
            return list(self.keys)

        def remove_api_key(self, key):
            self.keys.remove(key)

    runtime.cpa = FakeCPA()
    runtime.worker.reconcile_keys()
    assert runtime.cpa.keys == [keys["bob"]["key"], "external-key"]
    login(client, "alice")
    assert client.get("/api/keys").json() == {"items": [], "max_keys": 10}
    assert client.get("/api/usage/logs").json()["total"] == 1
    assert client.post(f"/api/keys/{keys['alice']['id']}/reveal").status_code == 404
    assert (
        client.patch(f"/api/keys/{keys['alice']['id']}", json={"status": "active"}).status_code
        == 404
    )


def test_update_started_before_admin_deletion_cannot_restore_the_key(key_portal):
    client, runtime, users, keys = key_portal
    conn = runtime.db()
    try:
        stale = api_keys.get_owned(conn, users["alice"], keys["alice"]["id"])
        login(client, "admin")
        response = client.delete(f"/api/admin/users/{users['alice']}/keys/{stale['id']}")
        assert response.status_code == 200
        for changes in ({"status": "active"}, {"name": "restored"}, {}):
            with pytest.raises(ApiError) as exc:
                api_keys.update(conn, stale, changes)
            assert exc.value.status == 404
        row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (stale["id"],)).fetchone()
        assert row["status"] == KeyStatus.DELETED and row["name"] == stale["name"]
    finally:
        conn.close()


def test_admin_user_ledger_and_usage_stay_scoped_to_the_account(key_portal):
    client, runtime, users, keys = key_portal
    conn = runtime.db()
    try:
        admin_id = accounts.find_by_username(conn, "admin")["id"]
        for username in ("alice", "bob"):
            billing.apply_credit(
                conn, users[username], 1000000, TxType.ADMIN, note=username, operator_id=admin_id
            )
            conn.execute(
                "INSERT INTO usage_logs (event_hash, user_id, key_id, ts, model, cost_micro) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    username,
                    users[username],
                    keys[username]["id"],
                    now_ms(),
                    username + "-model",
                    2500,
                ),
            )
        code = "AAAA-BBBB-CCCC-DDDD"
        billing.apply_credit(
            conn, users["alice"], 500000, TxType.REDEEM, ref=code, note="兑换码充值"
        )
    finally:
        conn.close()

    login(client, "admin")
    path = f"/api/admin/users/{users['alice']}"
    ledger = client.get(f"{path}/billing/transactions").json()
    assert ledger["total"] == 2
    assert [(t["type"], t["ref"], t["operator"]) for t in ledger["items"]] == [
        (TxType.REDEEM, code, ""),
        (TxType.ADMIN, "", "admin"),
    ]
    logs = client.get(f"{path}/usage/logs").json()
    assert logs["total"] == 1 and logs["sum_cost"] == 0.0025
    assert (logs["items"][0]["model"], logs["items"][0]["key_name"]) == ("alice-model", "alice key")
    for detail in ("billing/transactions", "usage/logs"):
        assert client.get(f"/api/admin/users/99999/{detail}").status_code == 404

    # The account owner's own ledger keeps redeem codes masked and hides the operator.
    login(client, "alice")
    own = client.get("/api/billing/transactions").json()["items"][0]
    assert own["ref"] == "AAAA-****-****-DDDD" and "operator" not in own
