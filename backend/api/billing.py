"""HTTP endpoints for balances, recharge codes and online payment."""

import urllib.parse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

from api.dependencies import (
    client_ip,
    get_connection,
    get_runtime,
    json_body,
    origin_url,
    pagination,
    query_arg,
    require_admin,
    require_user,
)
from services import billing

router = APIRouter(tags=["billing"])


@router.get("/api/billing/transactions")
def list_transactions(request: Request, user=Depends(require_user), conn=Depends(get_connection)):
    return billing.list_transactions(conn, user["id"], *pagination(request))


@router.post("/api/billing/redeem")
def redeem(
    request: Request,
    user=Depends(require_user),
    body=Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    result = billing.redeem(conn, user["id"], body.get("code"), runtime.limiter, client_ip(request))
    runtime.worker.trigger()
    return result


@router.get("/api/billing/orders")
def list_orders(request: Request, user=Depends(require_user), conn=Depends(get_connection)):
    return billing.list_orders(conn, user["id"], *pagination(request))


@router.post("/api/billing/orders")
def create_order(
    request: Request,
    user=Depends(require_user),
    body=Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    return billing.create_order(
        conn,
        runtime.cfg,
        runtime.settings.get,
        runtime.limiter,
        user["id"],
        body,
        origin_url(request),
    )


@router.post("/api/admin/users/{user_id:int}/balance")
def adjust_balance(
    user_id: int,
    admin=Depends(require_admin),
    body=Depends(json_body),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    result = billing.adjust_balance(conn, user_id, admin["id"], body)
    runtime.worker.trigger()
    return result


@router.get("/api/admin/codes")
def list_codes(request: Request, admin=Depends(require_admin), conn=Depends(get_connection)):
    return billing.list_codes(
        conn,
        *pagination(request),
        status=query_arg(request, "status"),
        batch=query_arg(request, "batch") or "",
        query=query_arg(request, "q") or "",
    )


@router.post("/api/admin/codes")
def create_codes(
    admin=Depends(require_admin), body=Depends(json_body), conn=Depends(get_connection)
):
    return billing.create_codes(conn, admin["id"], body)


@router.delete("/api/admin/codes/{code}")
def delete_code(code: str, admin=Depends(require_admin), conn=Depends(get_connection)):
    return billing.delete_code(conn, code)


async def _callback_params(request):
    params = dict(request.query_params)
    content_type = (request.headers.get("Content-Type") or "").lower()
    body = await request.body()
    if body and "application/x-www-form-urlencoded" in content_type:
        form = urllib.parse.parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
        params.update({key: values[-1] for key, values in form.items()})
    return params


async def _settle_callback(request, conn, runtime):
    params = await _callback_params(request)
    ok, order_no, changed = await run_in_threadpool(billing.settle_epay, conn, runtime.cfg, params)
    if changed:
        runtime.worker.trigger()
    return ok, order_no


@router.get("/api/pay/epay/notify")
@router.post("/api/pay/epay/notify")
async def epay_notify(request: Request, conn=Depends(get_connection), runtime=Depends(get_runtime)):
    ok, _ = await _settle_callback(request, conn, runtime)
    return PlainTextResponse("success" if ok else "fail")


@router.get("/api/pay/epay/return")
async def epay_return(request: Request, conn=Depends(get_connection), runtime=Depends(get_runtime)):
    ok, order_no = await _settle_callback(request, conn, runtime)
    query = urllib.parse.urlencode({"order": order_no, "result": "success" if ok else "pending"})
    return RedirectResponse("/recharge?" + query, status_code=302)
