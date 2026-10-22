"""HTTP endpoints for public model pricing and administrator price settings."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, get_runtime, json_body, require_admin
from services import pricing

router = APIRouter(tags=["pricing"])


# ---- User endpoints ----


@router.get("/api/prices")
def list_prices(conn=Depends(get_connection), runtime=Depends(get_runtime)):
    return pricing.list_prices(
        conn, runtime.worker.cpamp_prices(), runtime.settings.get, runtime.cfg["currency_symbol"]
    )


# ---- Administrator endpoints ----


@router.get("/api/admin/prices")
def admin_list_prices(
    admin=Depends(require_admin), conn=Depends(get_connection), runtime=Depends(get_runtime)
):
    return pricing.admin_list_prices(conn, runtime.worker.cpamp_prices(), runtime.settings.get)


@router.put("/api/admin/prices")
def admin_upsert_price(
    admin=Depends(require_admin), body=Depends(json_body), conn=Depends(get_connection)
):
    return pricing.upsert_price(conn, body)


@router.post("/api/admin/prices/delete")
def admin_delete_price(
    admin=Depends(require_admin), body=Depends(json_body), conn=Depends(get_connection)
):
    return pricing.delete_price(conn, str(body.get("model") or ""))


@router.post("/api/admin/prices/visibility")
def admin_set_visibility(
    admin=Depends(require_admin), body=Depends(json_body), conn=Depends(get_connection)
):
    return pricing.set_visibility(conn, body)
