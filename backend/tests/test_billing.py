"""Financial operations keep their transaction and pricing contracts after extraction."""

from copy import deepcopy

import pytest

from core.config import load_config
from core.constants import OrderStatus, RedeemType
from core.db import connect, init_db, transaction
from core.security import RateLimiter
from integrations import epay
from services import billing, pricing


@pytest.fixture
def billing_conn(tmp_path):
    path = str(tmp_path / "billing.sqlite")
    init_db(path)
    conn = connect(path)
    conn.execute(
        "INSERT INTO users(id, username, password_hash, balance_micro, created_at) "
        "VALUES (1, 'customer', 'unused', 10000000, 1)"
    )
    try:
        yield conn
    finally:
        conn.close()


def payment_config():
    cfg = deepcopy(load_config())
    cfg["payment"]["epay"].update(
        enabled=True,
        gateway="https://pay.example.test",
        pid="merchant",
        key="test-key",
        site_url="https://portal.example.test",
    )
    return cfg


def signed_callback(cfg, order_no, **changes):
    params = {
        "pid": "merchant",
        "out_trade_no": order_no,
        "trade_no": "gateway-trade",
        "trade_status": "TRADE_SUCCESS",
        "money": "12.34",
    }
    params.update(changes)
    params["sign"] = epay.sign(params, cfg["payment"]["epay"]["key"])
    return params


def test_payment_callback_credits_once_and_reports_changed(billing_conn):
    cfg = payment_config()
    order = billing.create_order(
        billing_conn,
        cfg,
        lambda _: "Test portal",
        RateLimiter(),
        1,
        {"channel": "alipay", "amount": "12.349"},
        "https://fallback.example.test",
    )
    order_no = order["order_no"]
    assert billing.settle_epay(billing_conn, cfg, signed_callback(cfg, order_no, money="99")) == (
        False,
        order_no,
        False,
    )
    params = signed_callback(cfg, order_no)
    assert billing.settle_epay(billing_conn, cfg, params) == (True, order_no, True)
    assert billing.settle_epay(billing_conn, cfg, params) == (True, order_no, False)
    user = billing_conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    assert user["balance_micro"] == 22340000
    assert user["total_recharge_micro"] == 12340000
    assert billing_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
    saved = billing_conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    assert saved["status"] == OrderStatus.PAID
    assert saved["pay_amount"] == "12.34"
    assert saved["trade_no"] == "gateway-trade"


def test_payment_callback_rejects_bad_signature_without_writing(billing_conn):
    cfg = payment_config()
    order = billing.create_order(
        billing_conn,
        cfg,
        lambda _: "Test portal",
        RateLimiter(),
        1,
        {"channel": "alipay", "amount": "12.34"},
        "https://fallback.example.test",
    )
    params = signed_callback(cfg, order["order_no"])
    params["sign"] = "invalid"
    assert billing.settle_epay(billing_conn, cfg, params) == (False, order["order_no"], False)
    assert billing_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
    assert billing_conn.execute("SELECT balance_micro FROM users").fetchone()[0] == 10000000


def test_create_codes_supports_cli_and_retries_collisions(billing_conn, monkeypatch):
    values = iter(["AAAA-BBBB-CCCC-DDDD", "AAAA-BBBB-CCCC-DDDD", "1111-2222-3333-4444"])
    monkeypatch.setattr(billing, "new_redeem_code", lambda: next(values))
    data = {"amount": "5", "count": 2, "batch": "cli-batch", "type": RedeemType.RECHARGE}
    codes = billing.create_codes(billing_conn, None, data)["codes"]
    assert codes == ["AAAA-BBBB-CCCC-DDDD", "1111-2222-3333-4444"]
    rows = billing_conn.execute("SELECT * FROM redeem_codes ORDER BY code").fetchall()
    assert len(rows) == 2
    assert all(row["amount_micro"] == 5000000 and row["created_by"] is None for row in rows)
    assert all(row["batch"] == "cli-batch" and row["expires_at"] is None for row in rows)
    result = billing.redeem(billing_conn, 1, "aaaabbbbccccdddd", RateLimiter(), "127.0.0.1")
    assert result == {"amount": 5, "balance": 15}


def test_code_generation_rolls_back_partial_batch(billing_conn, monkeypatch):
    values = iter(["AAAA-BBBB-CCCC-DDDD"])
    monkeypatch.setattr(billing, "new_redeem_code", lambda: next(values))
    with pytest.raises(StopIteration):
        billing.create_codes(
            billing_conn, None, {"amount": 5, "count": 2, "type": RedeemType.RECHARGE}
        )
    assert billing_conn.execute("SELECT COUNT(*) FROM redeem_codes").fetchone()[0] == 0


def test_usage_charge_rolls_back_with_its_caller(billing_conn):
    with pytest.raises(RuntimeError):
        with transaction(billing_conn):
            billing.charge_usage(billing_conn, 1, 2500000)
            raise RuntimeError("usage insertion failed")
    user = billing_conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    assert (user["balance_micro"], user["total_spent_micro"]) == (10000000, 0)
    with transaction(billing_conn):
        billing.charge_usage(billing_conn, 1, 2500000)
    user = billing_conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    assert (user["balance_micro"], user["total_spent_micro"]) == (7500000, 2500000)


def test_admin_balance_gift_recharge_and_deduction_statistics(admin_client, runtime):
    client = admin_client
    user_id = client.get("/api/user/me").json()["user"]["id"]
    url = f"/api/admin/users/{user_id}/balance"
    for payload, balance, recharge, tx_type, note in (
        ({"amount": 7, "type": "gift"}, 7, 0, "bonus", "管理员赠送"),
        ({"amount": 5, "type": "recharge", "note": "线下收款"}, 12, 5, "admin", "线下收款"),
        ({"amount": -3}, 9, 5, "admin", "管理员扣款"),
    ):
        response = client.post(url, json=payload)
        assert response.status_code == 200
        assert response.json() == {"balance": balance}
        user = client.get("/api/user/me").json()["user"]
        assert user["total_recharge"] == recharge and user["total_spent"] == 0
        overview = client.get("/api/admin/overview").json()
        assert overview["recharge"] == {"today": recharge, "month": recharge}
        assert sum(row["recharge"] for row in overview["daily"]) == recharge
        latest = client.get("/api/billing/transactions").json()["items"][0]
        assert latest["type"] == tx_type and latest["note"] == note
        assert latest["amount"] == payload["amount"] and latest["balance_after"] == balance
    conn = runtime.db()
    try:
        assert [row[0] for row in conn.execute("SELECT operator_id FROM transactions")] == [
            user_id,
            user_id,
            user_id,
        ]
    finally:
        conn.close()


def test_admin_positive_adjustment_requires_type(admin_client):
    client = admin_client
    user_id = client.get("/api/user/me").json()["user"]["id"]
    for payload in ({"amount": 5}, *({"amount": 5, "type": t} for t in (None, "", "bonus", []))):
        assert client.post(f"/api/admin/users/{user_id}/balance", json=payload).status_code == 400
    assert client.get("/api/user/me").json()["user"]["balance"] == 0
    assert client.get("/api/billing/transactions").json()["total"] == 0


def test_pricing_precedence_aliases_and_public_visibility(billing_conn):
    settings = {
        "default_input_price": 7,
        "default_output_price": 14,
        "cpamp_price_multiplier": 2,
        "use_cpamp_prices": True,
    }
    external = pricing.prices_from_external(
        {
            "Demo": {"input": 2, "output": 4, "cache_read": 0.2, "cache_write": 2.5},
        }
    )
    pricing.upsert_price(billing_conn, {"model": "Demo", "input": 3, "output": 6})
    book = pricing.build_price_book(billing_conn, external, settings.get)
    overridden, source = book.resolve("Demo")
    assert source == "override"
    assert overridden.cost_micro(1000000, 0, 0, 0) == 3000000
    alias, source = book.resolve("vendor/demo")
    assert source == "cpamp"
    assert alias.as_dict() == {"input": 4, "output": 8, "cache_read": 0.4, "cache_write": 5}
    fallback, source = book.resolve("unknown-model")
    assert source == "default"
    assert fallback.output == 14
    pricing.set_visibility(billing_conn, {"model": "Demo", "hidden": True})
    assert pricing.list_prices(billing_conn, external, settings.get, "$")["items"] == []
    assert (
        pricing.admin_list_prices(billing_conn, external, settings.get)["items"][0]["hidden"]
        is True
    )
