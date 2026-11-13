"""Node routing settings: whether nginx spreads users over the CPA nodes, and how.

The settings live in the settings table. The sync worker serializes them into the
string that deploy/cpa-router/cpa_route.lua accepts and pushes it to nginx.
"""

from core.db import get_setting, set_setting
from core.errors import ApiError

SETTING_KEY = "node_routing"
DEFAULT_CAPACITY = 1
MAX_CAPACITY = 1000


def load(conn, node_ids):
    """Return the settings for the configured nodes, filling in defaults.

    Routing starts switched off, so requests keep going to the first node until an
    administrator turns it on.
    """
    stored = get_setting(conn, SETTING_KEY, {}) or {}
    saved_nodes = stored.get("nodes") or {}
    return {
        "enabled": bool(stored.get("enabled", False)),
        "nodes": [
            {
                "id": node_id,
                "enabled": bool(saved_nodes.get(node_id, {}).get("enabled", True)),
                "capacity": saved_nodes.get(node_id, {}).get("capacity", DEFAULT_CAPACITY),
            }
            for node_id in node_ids
        ],
    }


def save(conn, node_ids, data):
    """Store the settings sent by the routing page and return them as load() does."""
    by_id = {item.get("id"): item for item in data.get("nodes") or [] if isinstance(item, dict)}
    nodes = {}
    for node_id in node_ids:
        item = by_id.get(node_id, {})
        try:
            # Two decimals keep Python's and Lua's number formatting identical, so the
            # worker can compare the configuration nginx holds with the saved one.
            capacity = round(float(item.get("capacity", DEFAULT_CAPACITY)), 2)
        except (TypeError, ValueError):
            capacity = 0
        if not 0 < capacity <= MAX_CAPACITY:
            raise ApiError(400, "%s 的容量比例需大于 0 且不超过 %d" % (node_id, MAX_CAPACITY))
        nodes[node_id] = {
            "enabled": bool(item.get("enabled", True)),
            "capacity": int(capacity) if capacity.is_integer() else capacity,
        }
    enabled = bool(data.get("enabled"))
    if enabled and not any(node["enabled"] for node in nodes.values()):
        raise ApiError(400, "开启分流时至少要有一个节点参与分流")
    set_setting(conn, SETTING_KEY, {"enabled": enabled, "nodes": nodes})
    return load(conn, node_ids)


def serialize(settings):
    """Format accepted by cpa_route.lua: "on;node1=3;node2=1" (off, or the participating nodes)."""
    parts = ["on" if settings["enabled"] else "off"]
    parts += [
        "%s=%s" % (node["id"], node["capacity"]) for node in settings["nodes"] if node["enabled"]
    ]
    return ";".join(parts)
