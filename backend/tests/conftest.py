"""Isolated application fixtures; no production configuration or data is loaded."""

import copy

import pytest
from fastapi.testclient import TestClient

from core.config import load_config
from runtime.app import Runtime, create_app
from services import accounts


@pytest.fixture
def runtime(tmp_path):
    cfg = copy.deepcopy(load_config())
    cfg["data_dir"] = str(tmp_path / "data")
    cfg["frontend_dir"] = str(tmp_path / "frontend")
    cfg["cpamp"]["usage_db"] = str(tmp_path / "missing-cpamp.sqlite")
    cfg["cpa"]["management_key"] = ""
    return Runtime(cfg)


@pytest.fixture
def client(runtime):
    with TestClient(create_app(runtime=runtime, start_worker=False)) as client:
        client.headers["X-Requested-With"] = "portal"
        yield client


@pytest.fixture
def admin_client(client, runtime):
    conn = runtime.db()
    try:
        accounts.create_admin(conn, "admin", "admin-password")
    finally:
        conn.close()
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin-password"}
        ).status_code
        == 200
    )
    return client
