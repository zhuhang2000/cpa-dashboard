"""Gift codes credit balances without being reported as paid recharges."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.config import load_config
from core.constants import RedeemStatus, RedeemType, TxType
from core.db import SCHEMA_V1, connect, init_db, now_ms
from core.errors import ApiError
from core.security import RateLimiter
from runtime.app import Runtime, create_app
from services import accounts, billing


@pytest.fixture
def redeem_portal(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "core" / ".env.example")
    cfg.update(data_dir=str(tmp_path / "data"), frontend_dir=str(tmp_path / "frontend"))
    cfg["cpamp"]["usage_db"] = ""
    cfg["cpa"]["management_key"] = ""
    runtime = Runtime(cfg)
    conn = runtime.db()
    try:
        admin, _ = accounts.create_admin(conn, "admin", "test-password")
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("alice", admin["password_hash"], now_ms()),
        )
    finally:
        conn.close()
    with TestClient(create_app(runtime=runtime, start_worker=False)) as client:
        client.headers["X-Requested-With"] = "portal"
        yield client, runtime


def login(client, username):
    response = client.post(
        "/api/auth/login", json={"username": username, "password": "test-password"}
    )
    assert response.status_code == 200


def test_delete_codes_removes_unused_and_disabled_but_preserves_redeemed(redeem_portal):
    client, runtime = redeem_portal
    login(client, "admin")
    response = client.post("/api/admin/codes", json={"amount": 5, "count": 3, "type": "recharge"})
    assert response.status_code == 200
    unused, disabled, used = response.json()["codes"]
    conn = runtime.db()
    try:
        conn.execute("UPDATE redeem_codes SET status = 'disabled' WHERE code = ?", (disabled,))
        conn.execute("UPDATE redeem_codes SET expires_at = 1 WHERE code = ?", (unused,))
    finally:
        conn.close()

    login(client, "alice")
    assert client.delete(f"/api/admin/codes/{unused}").status_code == 403
    assert client.post("/api/billing/redeem", json={"code": used}).status_code == 200
    login(client, "admin")
    for code in (unused, disabled):
        assert client.delete(f"/api/admin/codes/{code}").status_code == 200
        assert client.delete(f"/api/admin/codes/{code}").status_code == 400
    assert client.delete(f"/api/admin/codes/{used}").status_code == 400
    listing = client.get("/api/admin/codes").json()
    assert listing["total"] == 1
    assert listing["items"][0]["code"] == used

    conn = runtime.db()
    try:
        assert [row[0] for row in conn.execute("SELECT code FROM redeem_codes")] == [used]
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
        assert billing.recharge_totals(conn, 0) == 5000000
    finally:
        conn.close()
    login(client, "alice")
    for code in (unused, disabled):
        assert client.post("/api/billing/redeem", json={"code": code}).status_code == 400
    assert client.get("/api/user/me").json()["user"]["balance"] == 5


def test_v1_migration_preserves_existing_codes_balances_and_recharge_history(tmp_path):
    path = tmp_path / "legacy.sqlite"
    used_code = "AAAA-BBBB-CCCC-DDDD"
    unused_code = "EEEE-FFFF-GGGG-HHHH"
    stamp = now_ms()
    conn = connect(path)
    try:
        conn.executescript(SCHEMA_V1 + "\nPRAGMA user_version = 1;")
        user_id = conn.execute(
            "INSERT INTO users (username, password_hash, balance_micro, total_recharge_micro, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            ("legacy", "unused-password-hash", 7000000, 7000000, stamp),
        ).lastrowid
        conn.executemany(
            "INSERT INTO redeem_codes (code, amount_micro, status, created_at, used_by, used_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (used_code, 7000000, RedeemStatus.USED, stamp, user_id, stamp),
                (unused_code, 11000000, RedeemStatus.UNUSED, stamp, None, None),
            ],
        )
        conn.execute(
            "INSERT INTO transactions (user_id, type, amount_micro, balance_after_micro, ref, "
            "note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, TxType.REDEEM, 7000000, 7000000, used_code, "兑换码充值", stamp),
        )
        original_user = dict(accounts.get(conn, user_id))
        original_ledger = dict(conn.execute("SELECT * FROM transactions").fetchone())
        original_codes = [
            dict(row) for row in conn.execute("SELECT * FROM redeem_codes ORDER BY code")
        ]
    finally:
        conn.close()

    init_db(path)
    init_db(path)
    conn = connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert dict(accounts.get(conn, user_id)) == original_user
        assert dict(conn.execute("SELECT * FROM transactions").fetchone()) == original_ledger
        migrated = [dict(row) for row in conn.execute("SELECT * FROM redeem_codes ORDER BY code")]
        assert migrated == [{**row, "type": RedeemType.RECHARGE} for row in original_codes]
        limiter = RateLimiter()
        with pytest.raises(ApiError) as exc:
            billing.redeem(conn, user_id, used_code, limiter, "127.0.0.1")
        assert exc.value.status == 400
        assert billing.redeem(conn, user_id, unused_code, limiter, "127.0.0.1") == {
            "amount": 11,
            "balance": 18,
        }
        assert accounts.get(conn, user_id)["total_recharge_micro"] == 18000000
        assert billing.recharge_totals(conn, 0) == 18000000
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
    finally:
        conn.close()


def test_admin_only_generation_requires_valid_type(redeem_portal):
    client, runtime = redeem_portal
    for username, status in ((None, 401), ("alice", 403)):
        if username:
            login(client, username)
        assert client.get("/api/admin/codes").status_code == status
        assert (
            client.post("/api/admin/codes", json={"amount": 5, "type": "gift"}).status_code
            == status
        )

    login(client, "admin")
    for invalid_type in (None, "", "bonus", [], {}):
        response = client.post("/api/admin/codes", json={"amount": 5, "type": invalid_type})
        assert response.status_code == 400
    assert client.get("/api/admin/codes").json()["total"] == 0
    conn = runtime.db()
    try:
        with pytest.raises(ApiError) as exc:
            billing.generate_codes(conn, 5000000, 1, None, None, None, code_type="invalid")
        assert exc.value.status == 400
    finally:
        conn.close()

    response = client.post("/api/admin/codes", json={"amount": 5})
    assert response.status_code == 400
    assert client.get("/api/admin/codes").json()["total"] == 0
    response = client.post("/api/admin/codes", json={"amount": 5, "type": "recharge"})
    assert response.status_code == 200
    assert response.json()["type"] == RedeemType.RECHARGE
    listed = client.get("/api/admin/codes").json()["items"]
    assert len(listed) == 1
    assert listed[0]["code"] == response.json()["codes"][0]
    assert listed[0]["type"] == RedeemType.RECHARGE


def test_gifts_credit_once_without_entering_user_or_admin_recharge_statistics(redeem_portal):
    client, runtime = redeem_portal
    login(client, "admin")
    codes = {}
    for code_type, amount in ((RedeemType.GIFT, 7.5), (RedeemType.RECHARGE, 12.25)):
        response = client.post(
            "/api/admin/codes", json={"amount": amount, "count": 1, "type": code_type}
        )
        assert response.status_code == 200
        assert response.json()["type"] == code_type
        codes[code_type] = response.json()["codes"][0]
    listed = client.get("/api/admin/codes").json()["items"]
    assert {item["code"]: item["type"] for item in listed} == {
        code: code_type for code_type, code in codes.items()
    }

    for code_type, amount, balance, recharge in (
        (RedeemType.GIFT, 7.5, 7.5, 0),
        (RedeemType.RECHARGE, 12.25, 19.75, 12.25),
    ):
        login(client, "alice")
        # The persisted code type, not a caller-supplied type, controls accounting.
        forged_type = RedeemType.RECHARGE if code_type == RedeemType.GIFT else RedeemType.GIFT
        response = client.post(
            "/api/billing/redeem", json={"code": codes[code_type], "type": forged_type}
        )
        assert response.status_code == 200
        assert response.json() == {"amount": amount, "balance": balance}
        assert runtime.worker._wake.is_set()
        runtime.worker._wake.clear()
        assert (
            client.post("/api/billing/redeem", json={"code": codes[code_type]}).status_code == 400
        )
        assert not runtime.worker._wake.is_set()
        user = client.get("/api/user/me").json()["user"]
        assert user["balance"] == balance and user["total_recharge"] == recharge

        ledger = client.get("/api/billing/transactions").json()["items"]
        latest = ledger[0]
        expected_tx = TxType.REDEEM_GIFT if code_type == RedeemType.GIFT else TxType.REDEEM
        assert latest["type"] == expected_tx
        assert latest["amount"] == amount and latest["balance_after"] == balance
        assert latest["ref"] != codes[code_type] and "****" in latest["ref"]
        assert sum(item["amount"] for item in ledger) == balance

        login(client, "admin")
        overview = client.get("/api/admin/overview").json()
        assert overview["balance_total"] == balance
        assert overview["recharge"] == {"today": recharge, "month": recharge}
        assert sum(day["recharge"] for day in overview["daily"]) == recharge
        listed_user = client.get("/api/admin/users", params={"q": "alice"}).json()["items"][0]
        assert listed_user["balance"] == balance and listed_user["total_recharge"] == recharge

    conn = runtime.db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
        assert {row[0] for row in conn.execute("SELECT status FROM redeem_codes")} == {
            RedeemStatus.USED
        }
    finally:
        conn.close()
