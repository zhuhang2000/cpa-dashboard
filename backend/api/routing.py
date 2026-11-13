"""Node routing page: routing settings, nginx's live routing state and node sync status."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, get_runtime, json_body, require_admin
from integrations.router import RouterError
from services import routing

router = APIRouter(tags=["routing"])


def _node_ids(runtime):
    return [node.id for node in runtime.nodes]


def _view(conn, runtime, live=None):
    settings = routing.load(conn, _node_ids(runtime))
    client, state = runtime.router, runtime.worker.router_state
    nginx = {
        "configured": client.configured,
        "error": state["error"],
        "applied": None,
        "nodes": {},
        "last_sync_at": state["last_sync_at"],
        "sync_interval_seconds": runtime.cfg["cpamp"]["sync_interval_seconds"],
    }
    if client.configured:
        if live is None:
            try:
                live = client.status()
            except RouterError as exc:
                nginx["error"] = str(exc)
        if live is not None:
            nginx["applied"] = live.get("config") == routing.serialize(settings)
            nginx["nodes"] = {item.get("id"): item for item in live["nodes"]}
            # nginx holds the saved settings, so an error from an earlier round is stale.
            # Otherwise keep it: a refused push (HTTP 400) explains why they differ.
            if nginx["applied"]:
                nginx["error"] = None
    return {"routing": settings, "nginx": nginx, "nodes": runtime.worker.status()}


# ---- Administrator endpoints ----


@router.get("/api/admin/routing", dependencies=[Depends(require_admin)])
def admin_get_routing(conn=Depends(get_connection), runtime=Depends(get_runtime)):
    return _view(conn, runtime)


@router.put("/api/admin/routing", dependencies=[Depends(require_admin)])
def admin_put_routing(
    data: dict = Depends(json_body), conn=Depends(get_connection), runtime=Depends(get_runtime)
):
    routing.save(conn, _node_ids(runtime), data)
    return _view(conn, runtime, runtime.worker.sync_routing())
