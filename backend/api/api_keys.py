"""Authenticated API key endpoints and their response representation."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, get_runtime, json_body, require_admin, require_user
from core.db import now_ms
from services import accounts, api_keys
from services.billing import money

router = APIRouter(tags=["api_keys"])


def _mask(key, prefix):
    return key[: len(prefix) + 4] + "…" + key[-4:]


def to_public(cfg, row, user):
    return {
        "id": row["id"],
        "name": row["name"],
        "masked": _mask(row["key"], api_keys.key_prefix(cfg)),
        "status": row["status"],
        "state": api_keys.state(row, user, api_keys.min_balance_micro(cfg), now_ms()),
        "quota": None if row["quota_micro"] is None else money(row["quota_micro"]),
        "used": money(row["used_micro"]),
        "request_count": row["request_count"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "last_used_at": row["last_used_at"],
    }


# ---- User endpoints ----


@router.get("/api/keys")
def list_keys(
    user=Depends(require_user), conn=Depends(get_connection), runtime=Depends(get_runtime)
):
    rows = api_keys.list_for_user(conn, user["id"])
    return {
        "items": [to_public(runtime.cfg, row, user) for row in rows],
        "max_keys": api_keys.max_keys(runtime.cfg),
    }


@router.post("/api/keys")
def create_key(
    user=Depends(require_user),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    row = api_keys.create(conn, runtime.cfg, user["id"], data)
    runtime.worker.trigger()
    return {"key": row["key"], "item": to_public(runtime.cfg, row, user)}


@router.patch("/api/keys/{key_id:int}")
def update_key(
    key_id: int,
    user=Depends(require_user),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    row = api_keys.get_owned(conn, user["id"], key_id)
    row = api_keys.update(conn, row, data)
    runtime.worker.trigger()
    return {"item": to_public(runtime.cfg, row, user)}


@router.delete("/api/keys/{key_id:int}")
def delete_key(
    key_id: int,
    user=Depends(require_user),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    api_keys.soft_delete(conn, api_keys.get_owned(conn, user["id"], key_id))
    runtime.worker.trigger()
    return {"ok": True}


@router.post("/api/keys/{key_id:int}/reveal")
def reveal_key(key_id: int, user=Depends(require_user), conn=Depends(get_connection)):
    return {"key": api_keys.get_owned(conn, user["id"], key_id)["key"]}


# ---- Administrator endpoints ----


@router.get("/api/admin/users/{user_id:int}/keys", dependencies=[Depends(require_admin)])
def admin_list_keys(user_id: int, conn=Depends(get_connection), runtime=Depends(get_runtime)):
    user = accounts.get(conn, user_id)
    return {
        "items": [
            {**to_public(runtime.cfg, row, user), "key": row["key"]}
            for row in api_keys.list_for_user(conn, user_id)
        ]
    }


@router.delete(
    "/api/admin/users/{user_id:int}/keys/{key_id:int}", dependencies=[Depends(require_admin)]
)
def admin_delete_key(
    user_id: int, key_id: int, conn=Depends(get_connection), runtime=Depends(get_runtime)
):
    api_keys.soft_delete(conn, api_keys.get_owned(conn, user_id, key_id))
    runtime.worker.trigger()
    return {"ok": True}
