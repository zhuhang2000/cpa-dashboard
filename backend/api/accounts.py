"""Account, authentication and administrator user endpoints."""

from fastapi import APIRouter, Depends, Request, Response

from api.dependencies import (
    clear_session_cookie,
    client_ip,
    current_user,
    get_connection,
    get_runtime,
    json_body,
    pagination,
    require_admin,
    require_user,
    set_session_cookie,
)
from core.errors import ApiError
from services import accounts, api_keys
from services.billing import money

router = APIRouter(tags=["accounts"], dependencies=[Depends(current_user)])


def user_public(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"] or "",
        "role": row["role"],
        "status": row["status"],
        "balance": money(row["balance_micro"]),
        "total_recharge": money(row["total_recharge_micro"]),
        "total_spent": money(row["total_spent_micro"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


# ---- User endpoints ----


def _registration_allowed(runtime=Depends(get_runtime)):
    if not runtime.settings.get("allow_register"):
        raise ApiError(403, "当前未开放注册")


@router.post("/api/auth/register", dependencies=[Depends(_registration_allowed)])
def register(
    request: Request,
    response: Response,
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    row, token, max_age = accounts.register(
        conn,
        data,
        client_ip(request),
        runtime.limiter,
        runtime.settings.get("allow_register"),
        runtime.settings.get("signup_bonus"),
        runtime.cfg.get("session_days"),
        request.headers.get("User-Agent", ""),
    )
    set_session_cookie(request, response, token, max_age)
    return {"user": user_public(row)}


@router.post("/api/auth/login")
def login(
    request: Request,
    response: Response,
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    row, token, max_age = accounts.login(
        conn,
        data,
        client_ip(request),
        runtime.limiter,
        runtime.cfg.get("session_days"),
        request.headers.get("User-Agent", ""),
    )
    set_session_cookie(request, response, token, max_age)
    return {"user": user_public(row)}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response, conn=Depends(get_connection)):
    accounts.logout(conn, getattr(request.state, "session_hash", None))
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/api/user/me")
def get_me(user=Depends(current_user), conn=Depends(get_connection)):
    if user is None:
        return {"user": None, "key_count": 0}
    return {"user": user_public(user), "key_count": api_keys.count_live(conn, user["id"])}


@router.put("/api/user/profile")
def update_profile(
    user=Depends(require_user), data: dict = Depends(json_body), conn=Depends(get_connection)
):
    return {"user": user_public(accounts.update_profile(conn, user["id"], data))}


@router.post("/api/user/password")
def change_password(
    request: Request,
    user=Depends(require_user),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
):
    accounts.change_password(conn, user, data, request.state.session_hash)
    return {"ok": True}


# ---- Administrator endpoints ----


@router.get("/api/admin/users")
def admin_list_users(request: Request, admin=Depends(require_admin), conn=Depends(get_connection)):
    page, size, offset = pagination(request)
    q = (request.query_params.get("q") or "").strip()
    archived = request.query_params.get("archived") == "1"
    sort = request.query_params.get("sort") or "created"
    desc = request.query_params.get("order") != "asc"
    total, rows = accounts.search(conn, q, size, offset, archived, sort, desc)
    key_counts = api_keys.live_counts(conn, [row["id"] for row in rows])
    items = []
    for row in rows:
        item = user_public(row)
        item.update(
            key_count=key_counts.get(row["id"], 0),
            last_login_ip=row["last_login_ip"] or "",
            last_used_at=row["last_used_at"],
        )
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": size}


@router.post("/api/admin/users/archive")
def admin_archive_users(
    admin=Depends(require_admin), data: dict = Depends(json_body), conn=Depends(get_connection)
):
    return {"updated": accounts.set_archived(conn, data.get("ids"), data.get("archived"))}


@router.put("/api/admin/users/{user_id:int}/status")
def admin_set_user_status(
    user_id: int,
    admin=Depends(require_admin),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    row = accounts.set_status(conn, user_id, data.get("status"), admin["id"])
    # Key availability follows the account status, so sync CPA now.
    runtime.worker.trigger()
    return {"user": user_public(row)}


@router.put("/api/admin/users/{user_id:int}/role")
def admin_set_user_role(
    user_id: int,
    admin=Depends(require_admin),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
):
    row = accounts.set_role(conn, user_id, data.get("role"), admin["id"])
    return {"user": user_public(row)}


@router.post("/api/admin/users/{user_id:int}/password")
def admin_reset_password(
    user_id: int,
    admin=Depends(require_admin),
    data: dict = Depends(json_body),
    conn=Depends(get_connection),
):
    accounts.admin_reset_password(conn, user_id, data, admin["id"])
    return {"ok": True}
