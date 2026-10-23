"""Tag managers reach only the regular users sharing their tag, and only to credit them."""

import pytest

from core.constants import Role
from core.db import now_ms
from core.security import hash_password
from services import accounts


@pytest.fixture
def team(runtime):
    """An administrator, two VIP managers, a VIP member and a user outside the group."""
    password_hash = hash_password("test-password")
    conn = runtime.db()
    try:
        return {
            username: conn.execute(
                "INSERT INTO users (username, password_hash, role, tag, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, role, tag, now_ms()),
            ).lastrowid
            for username, role, tag in (
                ("root", Role.ADMIN, None),
                ("keeper", Role.MANAGER, "VIP"),
                ("peer", Role.MANAGER, "VIP"),
                ("alice", Role.USER, "VIP"),
                ("bob", Role.USER, None),
            )
        }
    finally:
        conn.close()


def login(client, username):
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "test-password"}
    )
    assert response.status_code == 200
    return response.json()["user"]


def test_manager_lists_and_reads_only_its_group(client, runtime, team):
    conn = runtime.db()
    try:
        accounts.set_archived(conn, [team["alice"]], True)
    finally:
        conn.close()
    me = login(client, "keeper")
    assert me["role"] == Role.MANAGER and "tag" not in me
    # Archiving is the administrator's housekeeping; the member stays in the manager's list.
    for params in ({}, {"archived": 1}, {"q": "ali"}):
        items = client.get("/api/admin/users", params=params).json()["items"]
        assert [item["username"] for item in items] == ["alice"]
        assert "tag" not in items[0]
    # The manager is never told its tag's name, not even by searching for it.
    assert client.get("/api/admin/users", params={"q": "VIP"}).json()["items"] == []
    for detail in ("billing/transactions", "usage/logs"):
        assert client.get(f"/api/admin/users/{team['alice']}/{detail}").status_code == 200
        for other in ("bob", "root", "keeper", "peer"):
            response = client.get(f"/api/admin/users/{team[other]}/{detail}")
            assert response.status_code == 404, (detail, other)

    # A member's tag stays internal and grants nothing.
    login(client, "alice")
    assert "tag" not in client.get("/api/user/me").json()["user"]
    assert client.get("/api/admin/users").status_code == 403


def test_manager_is_refused_every_other_administrator_action(client, team):
    login(client, "keeper")
    alice = team["alice"]
    for method, path, body in (
        ("GET", "/api/admin/overview", None),
        ("GET", "/api/admin/billing/transactions", None),
        ("GET", "/api/admin/tags", None),
        ("POST", "/api/admin/users/tag", {"ids": [alice], "tag": ""}),
        ("POST", "/api/admin/users/archive", {"ids": [alice], "archived": True}),
        ("PUT", f"/api/admin/users/{alice}/status", {"status": "banned"}),
        ("PUT", f"/api/admin/users/{alice}/role", {"role": "manager", "tag": "VIP"}),
        ("POST", f"/api/admin/users/{alice}/password", {"password": "replacement"}),
        ("GET", f"/api/admin/users/{alice}/keys", None),
        ("GET", "/api/admin/codes", None),
        ("GET", "/api/admin/settings", None),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == 403, (method, path)
        assert response.json() == {"error": "需要管理员权限"}


def test_manager_credits_its_members_but_cannot_gift(client, team):
    login(client, "keeper")
    path = f"/api/admin/users/{team['alice']}/balance"
    assert client.post(path, json={"amount": 5, "type": "recharge"}).json() == {"balance": 5}
    assert client.post(path, json={"amount": -2}).json() == {"balance": 3}
    response = client.post(path, json={"amount": 1, "type": "gift"})
    assert response.status_code == 403
    assert response.json() == {"error": "无权赠送余额，只能充值或扣款"}
    # Neither itself, another manager nor anyone outside the group can be credited.
    for other in ("keeper", "peer", "root", "bob"):
        response = client.post(
            f"/api/admin/users/{team[other]}/balance", json={"amount": 5, "type": "recharge"}
        )
        assert response.status_code == 404, other
    ledger = client.get(f"/api/admin/users/{team['alice']}/billing/transactions").json()
    assert [(item["amount"], item["operator"]) for item in ledger["items"]] == [
        (-2, "keeper"),
        (5, "keeper"),
    ]

    login(client, "root")
    assert client.post(path, json={"amount": 1, "type": "gift"}).json() == {"balance": 4}


def test_scope_follows_the_administrators_tag_and_role_changes(client, team):
    login(client, "root")
    response = client.put(f"/api/admin/users/{team['bob']}/role", json={"role": "manager"})
    assert response.status_code == 400
    assert response.json() == {"error": "请填写管理员负责的标签"}
    promoted = client.put(
        f"/api/admin/users/{team['bob']}/role", json={"role": "manager", "tag": "vip"}
    ).json()["user"]
    assert promoted["role"] == Role.MANAGER
    listed = client.get("/api/admin/users", params={"q": "bob"}).json()["items"]
    assert listed[0]["tag"] == "VIP"
    assert client.get("/api/admin/tags").json() == {
        "items": [{"tag": "VIP", "users": 1, "managers": 3}]
    }
    moved = client.post("/api/admin/users/tag", json={"ids": [team["alice"]], "tag": "Other"})
    assert moved.json() == {"updated": 1}
    client.put(f"/api/admin/users/{team['peer']}/role", json={"role": "user"})

    login(client, "keeper")
    assert client.get("/api/admin/users").json()["items"] == []
    assert client.get(f"/api/admin/users/{team['alice']}/usage/logs").status_code == 404
    # The demoted manager loses access on its next request and joins no group.
    me = login(client, "peer")
    assert me["role"] == Role.USER and "tag" not in me
    assert client.get("/api/admin/users").status_code == 403
