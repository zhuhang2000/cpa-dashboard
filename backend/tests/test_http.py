"""Transport and permission contracts that are easy to change during migration."""

from pathlib import Path

import pytest

from api.dependencies import get_connection
from core.db import now_ms


@pytest.mark.parametrize(
    ("method", "path", "status", "message"),
    [
        ("GET", "/api/keys", 401, "请先登录"),
        ("GET", "/api/admin/settings", 401, "请先登录"),
        ("GET", "/api/not-found", 404, "接口不存在"),
        ("POST", "/api/status", 405, "不支持的请求方法"),
        ("GET", "/api/keys/not-a-number", 404, "接口不存在"),
        ("GET", "/api/status/", 404, "接口不存在"),
        ("GET", "/api/docs", 401, "请先登录"),
        ("GET", "/api/openapi.json", 401, "请先登录"),
    ],
)
def test_api_errors(client, method, path, status, message):
    response = client.request(method, path)
    assert response.status_code == status
    assert response.json() == {"error": message}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"{", "请求体不是合法的 JSON"),
        (b"\xff", "请求体不是合法的 JSON"),
        (b"[]", "请求体必须是 JSON 对象"),
        (b"null", "请求体必须是 JSON 对象"),
        (b'"string"', "请求体必须是 JSON 对象"),
        (b"", "请输入用户名和密码"),
    ],
)
def test_json_contract(client, body, message):
    response = client.post(
        "/api/auth/login", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"error": message}


def test_csrf_content_type_and_body_limit(client):
    client.headers.pop("X-Requested-With")
    assert client.post("/api/auth/logout", json={}).json() == {"error": "非法请求来源"}
    client.headers["X-Requested-With"] = "portal"
    response = client.post("/api/auth/login", json={}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json()["error"] == "跨站请求被拒绝"
    response = client.post("/api/auth/login", content="a=b", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    response = client.post("/api/auth/login", content=b"x" * ((1 << 20) + 1))
    assert response.status_code == 413
    # The streamed request has no Content-Length; it must have the same bound.
    response = client.post("/api/auth/login", content=iter([b"x" * (1 << 20), b"x"]))
    assert response.status_code == 413
    # The payment gateway must be able to POST its signed form without CSRF headers.
    client.headers.pop("X-Requested-With")
    response = client.post("/api/pay/epay/notify", data={"out_trade_no": "missing"})
    assert response.status_code == 200 and response.text == "fail"


def test_auth_and_csrf_precede_json_errors(client):
    client.headers.pop("X-Requested-With")
    response = client.post(
        "/api/auth/login", content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 403
    client.headers["X-Requested-With"] = "portal"
    for path in (
        "/api/user/password",
        "/api/billing/orders",
        "/api/admin/codes",
        "/api/admin/prices/delete",
    ):
        response = client.post(path, content="{", headers={"Content-Type": "application/json"})
        assert response.status_code == 401


def test_session_cookie_renewal_logout_and_permissions(client, runtime):
    response = client.post(
        "/api/auth/register", json={"username": "member", "password": "password-123"}
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Lax" in response.headers["set-cookie"]
    assert client.get("/api/admin/settings").status_code == 403
    conn = runtime.db()
    try:
        conn.execute("UPDATE sessions SET expires_at = ?", (now_ms() + 10000,))
    finally:
        conn.close()
    response = client.get("/api/usage/logs?page=oops")
    assert response.status_code == 400
    assert "Max-Age=604800" in response.headers["set-cookie"]
    conn = runtime.db()
    try:
        conn.execute("UPDATE sessions SET expires_at = ?", (now_ms() + 10000,))
    finally:
        conn.close()
    response = client.post("/api/auth/logout")
    assert response.headers.get_list("set-cookie")[-1].endswith("Max-Age=0")
    assert client.get("/api/user/me").json()["user"] is None


def test_proxy_cookie_policy(client, runtime):
    runtime.cfg["trust_proxy"] = True
    response = client.post(
        "/api/auth/register",
        json={"username": "proxied", "password": "password-123"},
        headers={
            "X-Forwarded-Proto": "https",
            "X-Real-IP": "192.0.2.10",
            "X-Forwarded-Host": "portal.example",
            "Origin": "https://portal.example",
        },
    )
    assert response.status_code == 200
    assert response.headers["set-cookie"].endswith("; Secure")
    assert response.json()["user"]["username"] == "proxied"
    conn = runtime.db()
    try:
        assert conn.execute("SELECT ip FROM sessions").fetchone()[0] == "192.0.2.10"
    finally:
        conn.close()


def test_connection_cleanup_on_service_error(client, runtime):
    connections = []

    def tracked_connection():
        conn = runtime.db()
        connections.append(conn)
        try:
            yield conn
        finally:
            conn.close()

    client.app.dependency_overrides[get_connection] = tracked_connection
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 400 and len(connections) == 1
    import sqlite3

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")


def test_static_spa_cache_head_and_missing_assets(client, runtime):
    root = Path(runtime.cfg["frontend_dir"])
    assert client.get("/").status_code == 503
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>Portal</title>" + " " * 1500)
    (root / "assets" / "app.js").write_text("console.log('portal');" * 100)
    outside = root.parent / "secret.txt"
    outside.write_text("private")
    (root / "assets" / "linked.txt").symlink_to(outside)
    response = client.get("/dashboard")
    assert response.status_code == 200 and "Portal" in response.text
    assert response.headers["cache-control"] == "no-cache"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    response = client.get("/assets/app.js")
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["content-encoding"] == "gzip"
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/assets/linked.txt").status_code == 404
    assert client.get("/api/nonexistent").json() == {"error": "接口不存在"}
    assert client.post("/dashboard").status_code == 405
    for path in ("/dashboard", "/assets/app.js", "/api/status"):
        response = client.head(path)
        assert response.status_code == 200 and response.content == b""
        assert int(response.headers["content-length"]) > 0
        get = client.get(path)
        assert response.headers.get("content-encoding") == get.headers.get("content-encoding")
        assert response.headers["content-length"] == get.headers["content-length"]


def test_openapi_is_available_to_admin(admin_client):
    response = admin_client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/auth/login" in paths
    assert "post" in paths["/api/pay/epay/notify"] and "get" in paths["/api/pay/epay/notify"]
    assert "/api/keys/{key_id}" in paths
    assert admin_client.get("/api/docs").status_code == 200
