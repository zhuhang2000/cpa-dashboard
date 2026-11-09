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
    ledger = "billing/transactions"
    assert client.get(f"/api/admin/users/{team['alice']}/{ledger}").status_code == 200
    for other in ("bob", "root", "keeper", "peer"):
        response = client.get(f"/api/admin/users/{team[other]}/{ledger}")
        assert response.status_code == 404, other

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
        ("POST", f"/api/admin/users/{alice}/password", {"password": "replacement"}),
        ("GET", f"/api/admin/users/{alice}/keys", None),
        ("GET", f"/api/admin/users/{alice}/usage/logs", None),
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


def test_manager_aliases_its_members_for_all_staff_but_not_the_user(client, team):
    login(client, "keeper")
    path = f"/api/admin/users/{team['alice']}/alias"
    assert client.put(path, json={"alias": "张三"}).json() == {"ok": True}
    for other in ("keeper", "peer", "root", "bob"):
        response = client.put(f"/api/admin/users/{team[other]}/alias", json={"alias": "x"})
        assert response.status_code == 404, other
    found = client.get("/api/admin/users", params={"q": "张三"}).json()["items"]
    assert [(item["username"], item["alias"]) for item in found] == [("alice", "张三")]

    login(client, "root")
    listed = client.get("/api/admin/users", params={"q": "张三"}).json()["items"]
    assert [(item["username"], item["alias"]) for item in listed] == [("alice", "张三")]
    assert client.put(path, json={"alias": None}).json() == {"ok": True}
    cleared = client.get("/api/admin/users", params={"q": "alice"}).json()["items"]
    assert cleared[0]["alias"] == ""

    me = login(client, "alice")
    assert "alias" not in me and "alias" not in client.get("/api/user/me").json()["user"]
    assert client.put(path, json={"alias": "x"}).status_code == 403


def test_scope_follows_the_tags_the_administrator_sets(client, team):
    login(client, "root")
    path = "/api/admin/users/tag"
    assert client.post(path, json={"ids": [team["root"]], "tag": "VIP"}).json() == {"updated": 0}
    promoted = client.post(path, json={"ids": [team["bob"]], "tag": "VIP", "manager": True})
    assert promoted.json() == {"updated": 1}
    listed = client.get("/api/admin/users", params={"q": "bob"}).json()["items"]
    assert (listed[0]["role"], listed[0]["tag"]) == (Role.MANAGER, "VIP")
    assert client.get("/api/admin/tags").json() == {
        "items": [{"tag": "VIP", "users": 1, "managers": 3}]
    }
    moved = client.post(path, json={"ids": [team["alice"]], "tag": "Other"})
    assert moved.json() == {"updated": 1}
    client.post(path, json={"ids": [team["peer"]], "tag": None})

    login(client, "keeper")
    assert client.get("/api/admin/users").json()["items"] == []
    assert client.get(f"/api/admin/users/{team['alice']}/billing/transactions").status_code == 404
    # The demoted manager loses access on its next request and joins no group.
    me = login(client, "peer")
    assert me["role"] == Role.USER and "tag" not in me
    assert client.get("/api/admin/users").status_code == 403
