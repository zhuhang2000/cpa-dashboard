"""Exercise business endpoints through FastAPI with real temporary databases."""

import sqlite3
from copy import deepcopy

from fastapi.testclient import TestClient

from core.config import load_config
from core.db import now_ms
from core.security import sha256_hex
from integrations import epay
from runtime.app import Runtime, create_app

EXPECTED_ROUTES = {
    ("GET", "/api/status"),
    ("GET", "/api/pricing"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/user/me"),
    ("PUT", "/api/user/profile"),
    ("POST", "/api/user/password"),
    ("GET", "/api/keys"),
    ("POST", "/api/keys"),
    ("PATCH", "/api/keys/{key_id}"),
    ("DELETE", "/api/keys/{key_id}"),
    ("POST", "/api/keys/{key_id}/reveal"),
    ("GET", "/api/usage/summary"),
    ("GET", "/api/usage/logs"),
    ("GET", "/api/usage/export"),
    ("GET", "/api/billing/transactions"),
    ("POST", "/api/billing/redeem"),
    ("GET", "/api/billing/orders"),
    ("POST", "/api/billing/orders"),
    ("GET", "/api/pay/epay/notify"),
    ("POST", "/api/pay/epay/notify"),
    ("GET", "/api/pay/epay/return"),
    ("GET", "/api/admin/overview"),
    ("GET", "/api/admin/users"),
    ("PATCH", "/api/admin/users/{user_id}"),
    ("GET", "/api/admin/users/{user_id}/keys"),
    ("DELETE", "/api/admin/users/{user_id}/keys/{key_id}"),
    ("POST", "/api/admin/users/{user_id}/balance"),
    ("GET", "/api/admin/codes"),
    ("POST", "/api/admin/codes"),
    ("DELETE", "/api/admin/codes/{code}"),
    ("GET", "/api/admin/prices"),
    ("PUT", "/api/admin/prices"),
    ("POST", "/api/admin/prices/delete"),
    ("POST", "/api/admin/prices/visibility"),
    ("GET", "/api/admin/settings"),
    ("PUT", "/api/admin/settings"),
    ("POST", "/api/admin/sync"),
}


class FakeCPA:
    """Only the external management transport is fake; sync and accounting are real."""

    configured = True
    base = "https://cpa.example.test"

    def __init__(self):
        self.keys = ["foreign-key"]

    def list_api_keys(self):
        return list(self.keys)

    def add_api_key(self, key):
        if key not in self.keys:
            self.keys.append(key)

    def remove_api_key(self, key):
        self.keys.remove(key)

    def put_api_keys(self, keys):
        self.keys = list(keys)


def run_portal_scenario(admin, user, bootstrap_admin, append_usage, payment_key="test-payment-key"):
    """Reusable HTTP scenario; setup callbacks keep it independent of app internals.

    Clients need request(), headers and their own cookie jars. The returned
    response records can also be normalized for comparison with a legacy server.
    """
    covered, records = set(), []
    for client in (admin, user):
        client.headers["X-Requested-With"] = "portal"

    def call(client, method, path, expected=200, route=None, **kwargs):
        response = client.request(method, path, **kwargs)
        assert response.status_code == expected, (method, path, response.status_code, response.text)
        payload = (
            response.json()
            if "application/json" in response.headers.get("content-type", "")
            else response.text
        )
        covered.add((method, route or path))
        records.append(
            {
                "method": method,
                "route": route or path,
                "status": response.status_code,
                "body": payload,
                "location": response.headers.get("location"),
            }
        )
        return payload, response

    status, _ = call(admin, "GET", "/api/status")
    assert status["payment"]["online"] is True
    call(admin, "GET", "/api/pricing")
    registered, _ = call(
        admin,
        "POST",
        "/api/auth/register",
        json={
            "username": "scenario-admin",
            "password": "admin-password",
            "email": "admin@example.test",
        },
    )
    bootstrap_admin(registered["user"]["id"])
    call(admin, "POST", "/api/auth/logout", json={})
    logged_in, _ = call(
        admin,
        "POST",
        "/api/auth/login",
        json={
            "username": "scenario-admin",
            "password": "admin-password",
        },
    )
    assert logged_in["user"]["role"] == "admin"

    registered, _ = call(
        user,
        "POST",
        "/api/auth/register",
        json={
            "username": "scenario-user",
            "password": "user-password",
            "email": "user@example.test",
        },
    )
    user_id = registered["user"]["id"]
    me, _ = call(user, "GET", "/api/user/me")
    assert me["user"]["id"] == user_id and me["user"]["balance"] == 0
    profile, _ = call(user, "PUT", "/api/user/profile", json={"email": "updated@example.test"})
    assert profile["user"]["email"] == "updated@example.test"
    call(
        user,
        "POST",
        "/api/user/password",
        json={
            "old_password": "user-password",
            "new_password": "new-user-password",
        },
    )
    call(user, "GET", "/api/admin/overview", expected=403)

    keys, _ = call(user, "GET", "/api/keys")
    assert keys["items"] == []
    created, _ = call(user, "POST", "/api/keys", json={"name": "original", "quota": 20})
    key_id, secret = created["item"]["id"], created["key"]
    updated, _ = call(
        user,
        "PATCH",
        f"/api/keys/{key_id}",
        route="/api/keys/{key_id}",
        json={"name": "production", "quota": 40},
    )
    assert updated["item"]["name"] == "production" and updated["item"]["quota"] == 40
    revealed, _ = call(
        user, "POST", f"/api/keys/{key_id}/reveal", route="/api/keys/{key_id}/reveal", json={}
    )
    assert revealed["key"] == secret
    temporary, _ = call(user, "POST", "/api/keys", json={"name": "temporary"})
    temporary_id = temporary["item"]["id"]
    call(user, "DELETE", f"/api/keys/{temporary_id}", route="/api/keys/{key_id}")

    users, _ = call(admin, "GET", "/api/admin/users", params={"q": "scenario-user"})
    assert users["total"] == 1 and users["items"][0]["key_count"] == 1
    extra, _ = call(user, "POST", "/api/keys", json={"name": "unused-admin-cleanup"})
    managed, _ = call(
        admin, "GET", f"/api/admin/users/{user_id}/keys", route="/api/admin/users/{user_id}/keys"
    )
    assert {item["key"] for item in managed["items"]} == {secret, extra["key"]}
    call(
        admin,
        "DELETE",
        f"/api/admin/users/{user_id}/keys/{extra['item']['id']}",
        route="/api/admin/users/{user_id}/keys/{key_id}",
    )
    call(
        admin,
        "PATCH",
        f"/api/admin/users/{user_id}",
        route="/api/admin/users/{user_id}",
        json={"role": "user", "status": "active"},
    )
    balance, _ = call(
        admin,
        "POST",
        f"/api/admin/users/{user_id}/balance",
        route="/api/admin/users/{user_id}/balance",
        json={"amount": 10, "type": "recharge", "note": "initial credit"},
    )
    assert balance["balance"] == 10
    generated, _ = call(
        admin,
        "POST",
        "/api/admin/codes",
        json={"amount": 5, "count": 2, "batch": "scenario", "type": "recharge"},
    )
    codes = generated["codes"]
    listed, _ = call(
        admin, "GET", "/api/admin/codes", params={"batch": "scenario", "status": "unused"}
    )
    assert listed["total"] == 2
    call(admin, "DELETE", "/api/admin/codes/" + codes[1], route="/api/admin/codes/{code}")
    redeemed, _ = call(
        user, "POST", "/api/billing/redeem", json={"code": codes[0].replace("-", "").lower()}
    )
    assert redeemed == {"amount": 5, "balance": 15}
    call(user, "POST", "/api/billing/redeem", expected=400, json={"code": codes[0]})

    call(admin, "GET", "/api/admin/settings")
    settings, _ = call(
        admin,
        "PUT",
        "/api/admin/settings",
        json={
            "site_name": "Scenario portal",
            "announcement": "maintenance test",
            "cpamp_price_multiplier": 1.5,
        },
    )
    assert settings["settings"]["site_name"] == "Scenario portal"
    status, _ = call(user, "GET", "/api/status")
    assert status["site_name"] == "Scenario portal" and status["announcement"] == "maintenance test"
    call(
        admin,
        "PUT",
        "/api/admin/prices",
        json={"model": "demo-model", "input": 2, "output": 4, "note": "test price"},
    )
    prices, _ = call(admin, "GET", "/api/admin/prices")
    assert prices["items"][0]["source"] == "override"
    public, _ = call(user, "GET", "/api/pricing")
    assert public["items"][0]["input"] == 2
    call(
        admin, "POST", "/api/admin/prices/visibility", json={"model": "demo-model", "hidden": True}
    )
    public, _ = call(user, "GET", "/api/pricing")
    assert public["items"] == []
    call(
        admin, "POST", "/api/admin/prices/visibility", json={"model": "demo-model", "hidden": False}
    )

    append_usage(secret)
    synced, _ = call(admin, "POST", "/api/admin/sync", json={})
    assert synced["sync"]["cpamp"]["ok"] is True and synced["sync"]["cpamp"]["billed_events"] == 2
    call(admin, "POST", "/api/admin/sync", json={})
    summary, _ = call(user, "GET", "/api/usage/summary", params={"days": 7})
    assert summary["total"] == {"requests": 2, "cost": 3}
    assert summary["balance"] == 12 and len(summary["daily"]) == 7
    logs, _ = call(user, "GET", "/api/usage/logs", params={"key_id": key_id, "model": "demo-model"})
    assert logs["total"] == 2 and logs["sum_cost"] == 3
    failed, _ = call(user, "GET", "/api/usage/logs", params={"status": "failed"})
    assert failed["total"] == 1 and failed["sum_cost"] == 0
    exported, response = call(user, "GET", "/api/usage/export")
    assert "text/csv" in response.headers["content-type"]
    assert (
        "demo-model" in exported
        and "3.000000" in exported
        and "attachment" in response.headers["content-disposition"]
    )
    keys, _ = call(user, "GET", "/api/keys")
    assert len(keys["items"]) == 1 and keys["items"][0]["used"] == 3
    assert keys["items"][0]["request_count"] == 2

    order, _ = call(
        user, "POST", "/api/billing/orders", json={"channel": "alipay", "amount": "12.34"}
    )
    orders, _ = call(user, "GET", "/api/billing/orders")
    assert orders["total"] == 1 and orders["items"][0]["status"] == "pending"
    params = {
        "pid": "merchant",
        "out_trade_no": order["order_no"],
        "trade_no": "scenario-trade",
        "trade_status": "TRADE_SUCCESS",
        "money": "12.34",
    }
    params["sign"] = epay.sign(params, payment_key)
    result, _ = call(user, "GET", "/api/pay/epay/notify", params=params)
    assert result == "success"
    result, _ = call(user, "POST", "/api/pay/epay/notify", data=params)
    assert result == "success"
    _, returned = call(
        user, "GET", "/api/pay/epay/return", expected=302, params=params, follow_redirects=False
    )
    assert "result=success" in returned.headers["location"]
    orders, _ = call(user, "GET", "/api/billing/orders")
    assert orders["items"][0]["status"] == "paid" and orders["items"][0]["credit"] == 12.34
    ledger, _ = call(user, "GET", "/api/billing/transactions")
    assert ledger["total"] == 3
    assert {entry["type"] for entry in ledger["items"]} == {"admin", "redeem", "online"}
    assert all("****" in entry["ref"] for entry in ledger["items"] if entry["type"] == "redeem")
    me, _ = call(user, "GET", "/api/user/me")
    assert me["user"]["balance"] == 24.34 and me["user"]["total_spent"] == 3
    assert me["user"]["total_recharge"] == 27.34

    overview, _ = call(admin, "GET", "/api/admin/overview")
    assert overview["users"]["total"] == 2
    assert overview["usage"]["today"] == {"requests": 2, "cost": 3}
    assert overview["recharge"]["today"] == 27.34
    call(admin, "POST", "/api/admin/prices/delete", json={"model": "demo-model"})
    public, _ = call(user, "GET", "/api/pricing")
    assert public["items"][0]["source"] == "cpamp" and public["items"][0]["input"] == 1.5

    call(user, "POST", "/api/auth/logout", json={})
    call(
        user,
        "POST",
        "/api/auth/login",
        json={"username": "updated@example.test", "password": "new-user-password"},
    )
    call(
        admin,
        "PATCH",
        f"/api/admin/users/{user_id}",
        route="/api/admin/users/{user_id}",
        json={"status": "banned"},
    )
    logged_out, _ = call(user, "GET", "/api/user/me")
    assert logged_out == {"user": None, "key_count": 0}
    call(user, "GET", "/api/keys", expected=401)
    call(
        user,
        "POST",
        "/api/auth/login",
        expected=403,
        json={"username": "scenario-user", "password": "new-user-password"},
    )
    call(admin, "POST", "/api/admin/sync", json={})
    return covered, records


def test_all_business_endpoints_through_fastapi(tmp_path):
    cfg = deepcopy(load_config())
    cfg["data_dir"] = str(tmp_path / "portal")
    cfg["frontend_dir"] = str(tmp_path)
    cfg["cpamp"]["usage_db"] = str(tmp_path / "cpamp.sqlite")
    cfg["payment"]["epay"].update(
        enabled=True,
        gateway="https://pay.example.test",
        pid="merchant",
        key="test-payment-key",
        site_url="https://portal.example.test",
    )
    source = sqlite3.connect(cfg["cpamp"]["usage_db"])
    source.executescript("""
        CREATE TABLE usage_events (
            id INTEGER PRIMARY KEY, event_hash TEXT, timestamp_ms INTEGER, model TEXT,
            api_key_hash TEXT, input_tokens INTEGER, output_tokens INTEGER, failed INTEGER
        );
        CREATE TABLE model_prices (model TEXT, prompt_per_1m REAL, completion_per_1m REAL);
        INSERT INTO model_prices VALUES ('demo-model', 1, 2);
    """)
    source.close()
    runtime = Runtime(cfg)
    runtime.cpa = FakeCPA()

    def bootstrap_admin(user_id):
        conn = runtime.db()
        try:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
        finally:
            conn.close()

    def append_usage(secret):
        source = sqlite3.connect(cfg["cpamp"]["usage_db"])
        try:
            timestamp = now_ms()
            source.executemany(
                "INSERT INTO usage_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        1,
                        "scenario-success",
                        timestamp,
                        "demo-model",
                        sha256_hex(secret),
                        1000000,
                        250000,
                        0,
                    ),
                    (
                        2,
                        "scenario-failed",
                        timestamp + 1,
                        "demo-model",
                        sha256_hex(secret),
                        1000,
                        10,
                        1,
                    ),
                ],
            )
            source.commit()
        finally:
            source.close()

    app = create_app(runtime=runtime, start_worker=False)
    with TestClient(app) as admin, TestClient(app) as user:
        covered, records = run_portal_scenario(admin, user, bootstrap_admin, append_usage)
        actual_routes = {
            (method.upper(), path)
            for path, operations in app.openapi()["paths"].items()
            for method in operations
            if method in {"get", "post", "put", "patch", "delete"}
        }
    assert len(EXPECTED_ROUTES) == 39
    assert covered == EXPECTED_ROUTES
    assert actual_routes == EXPECTED_ROUTES
    assert len(records) > 39
    assert runtime.cpa.keys == ["foreign-key"]
    conn = runtime.db()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = 'scenario-user'").fetchone()
        assert (user["balance_micro"], user["total_spent_micro"], user["status"]) == (
            24340000,
            3000000,
            "banned",
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user["id"],)
            ).fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM usage_logs").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 3
    finally:
        conn.close()
