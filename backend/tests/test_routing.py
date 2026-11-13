"""Node routing settings, their push to nginx and the routing page endpoints."""

import pytest

from core.errors import ApiError
from integrations.router import RouterError
from services import routing

NODES = ["node1", "node2"]


class FakeRouter:
    """Stands in for nginx's control endpoint, which holds one configuration string."""

    configured = True

    def __init__(self, config=None):
        self.config = config
        self.pushes = []
        self.reachable = True
        self.refuse = False

    def _live(self):
        return {
            "config": self.config,
            "nodes": [
                {"id": "node1", "users": 2, "inflight": 1, "today": 30, "down": False},
                {"id": "node2", "users": 1, "inflight": 0, "today": 9, "down": True},
            ],
        }

    def status(self):
        if not self.reachable:
            raise RouterError("无法连接 nginx 分流接口: Connection refused")
        return self._live()

    def push(self, config):
        if self.refuse:
            raise RouterError('nginx 分流接口返回 HTTP 400: {"error":"invalid config"}')
        self.pushes.append(config)
        self.config = config
        return self._live()


@pytest.fixture
def conn(runtime):
    conn = runtime.db()
    yield conn
    conn.close()


def test_routing_starts_off_with_every_node_taking_part(conn):
    settings = routing.load(conn, NODES)
    assert settings == {
        "enabled": False,
        "nodes": [
            {"id": "node1", "enabled": True, "capacity": 1},
            {"id": "node2", "enabled": True, "capacity": 1},
        ],
    }
    assert routing.serialize(settings) == "off;node1=1;node2=1"


def test_saved_settings_serialize_only_participating_nodes(conn):
    saved = routing.save(
        conn,
        NODES,
        {
            "enabled": True,
            "nodes": [
                {"id": "node1", "enabled": True, "capacity": 3},
                {"id": "node2", "enabled": False, "capacity": 1.239},
                {"id": "node9", "enabled": True, "capacity": 5},
            ],
        },
    )
    assert saved["nodes"][1] == {"id": "node2", "enabled": False, "capacity": 1.24}
    assert routing.load(conn, NODES) == saved
    assert routing.serialize(saved) == "on;node1=3"
    saved["nodes"][1]["enabled"] = True
    assert routing.serialize(saved) == "on;node1=3;node2=1.24"


@pytest.mark.parametrize("capacity", [0, -1, 1001, "many", None])
def test_out_of_range_capacity_is_refused(conn, capacity):
    with pytest.raises(ApiError) as error:
        routing.save(conn, NODES, {"nodes": [{"id": "node1", "capacity": capacity}]})
    assert error.value.status == 400


def test_routing_on_needs_a_participating_node(conn):
    off = [{"id": node, "enabled": False, "capacity": 1} for node in NODES]
    with pytest.raises(ApiError) as error:
        routing.save(conn, NODES, {"enabled": True, "nodes": off})
    assert error.value.message == "开启分流时至少要有一个节点参与分流"
    assert routing.save(conn, NODES, {"enabled": False, "nodes": off})["enabled"] is False


def test_worker_pushes_only_when_nginx_holds_something_else(runtime):
    runtime.router = FakeRouter()
    assert runtime.worker.sync_routing()["config"] == "off;node1=1"
    runtime.worker.sync_routing()
    assert runtime.router.pushes == ["off;node1=1"]
    assert runtime.worker.router_state["ok"] is True

    # An nginx restart empties its shared memory; the next sync restores the settings.
    runtime.router.config = None
    runtime.worker.sync_routing()
    assert runtime.router.pushes == ["off;node1=1", "off;node1=1"]

    runtime.router.reachable = False
    assert runtime.worker.sync_routing() is None
    assert runtime.worker.router_state["ok"] is False
    assert "Connection refused" in runtime.worker.router_state["error"]


def test_worker_skips_routing_without_a_control_endpoint(runtime):
    assert runtime.router.configured is False
    assert runtime.worker.sync_routing() is None
    assert runtime.worker.router_state["ok"] is None


def test_routing_page_shows_live_state_and_saving_applies_at_once(admin_client, runtime):
    runtime.router = FakeRouter(config="off;node1=1")
    page = admin_client.get("/api/admin/routing").json()
    assert page["nginx"]["configured"] is True
    assert page["nginx"]["applied"] is True
    assert page["nginx"]["nodes"]["node1"]["users"] == 2
    assert [node["id"] for node in page["nodes"]] == ["node1"]

    response = admin_client.put(
        "/api/admin/routing",
        json={"enabled": True, "nodes": [{"id": "node1", "enabled": True, "capacity": 2}]},
    )
    assert response.status_code == 200
    assert runtime.router.pushes == ["on;node1=2"]
    assert response.json()["nginx"]["applied"] is True
    assert response.json()["routing"]["enabled"] is True


def test_routing_page_reports_an_unreachable_nginx(admin_client, runtime):
    runtime.router = FakeRouter()
    runtime.router.reachable = False
    page = admin_client.get("/api/admin/routing").json()
    assert page["nginx"]["applied"] is None
    assert "Connection refused" in page["nginx"]["error"]
    # Saving still keeps the settings; the worker pushes them once nginx answers again.
    response = admin_client.put("/api/admin/routing", json={"enabled": False, "nodes": []})
    assert response.status_code == 200
    assert runtime.router.pushes == []


def test_routing_page_keeps_a_refused_push_and_drops_a_stale_error(admin_client, runtime):
    runtime.router = FakeRouter(config="off;node1=1")
    runtime.router.refuse = True
    response = admin_client.put(
        "/api/admin/routing",
        json={"enabled": True, "nodes": [{"id": "node1", "enabled": True, "capacity": 1}]},
    )
    nginx = response.json()["nginx"]
    assert nginx["applied"] is False
    assert "invalid config" in nginx["error"]

    runtime.router.refuse = False
    runtime.worker.sync_routing()
    runtime.worker.router_state["error"] = "无法连接 nginx 分流接口: timed out"
    nginx = admin_client.get("/api/admin/routing").json()["nginx"]
    assert nginx["applied"] is True and nginx["error"] is None
    assert nginx["sync_interval_seconds"] > 0


def test_overview_only_names_the_nodes_with_sync_problems(admin_client):
    overview = admin_client.get("/api/admin/overview").json()
    assert "nodes" not in overview
    # The test runtime has no CPA management key, so node1 cannot receive keys.
    assert overview["sync_issues"] == ["node1"]
