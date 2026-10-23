"""Public site information and administrator runtime settings/sync actions."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, get_runtime, json_body, require_admin
from core.constants import VERSION
from core.errors import ApiError
from services.billing import epay_conf
from services.notices import latest_at

router = APIRouter(tags=["settings"])


# ---- User endpoints ----


@router.get("/api/status")
def get_status(runtime=Depends(get_runtime), conn=Depends(get_connection)):
    cfg, settings = runtime.cfg, runtime.settings
    pay, conf = cfg["payment"], epay_conf(cfg)
    return {
        "site_name": settings.get("site_name"),
        "public_api_base": settings.get("public_api_base"),
        "announcement": settings.get("announcement"),
        "notice_latest_at": latest_at(conn),
        "allow_register": settings.get("allow_register"),
        "currency_symbol": cfg["currency_symbol"],
        "max_keys_per_user": cfg["max_keys_per_user"],
        "payment": {
            "online": conf is not None,
            "channels": conf["channels"] if conf else [],
            "presets": pay["presets"],
            "min_amount": pay["min_amount"],
            "max_amount": pay["max_amount"],
            "credit_ratio": pay["credit_ratio"],
        },
        "version": VERSION,
    }


# ---- Administrator endpoints ----


@router.get("/api/admin/settings", dependencies=[Depends(require_admin)])
def admin_get_settings(runtime=Depends(get_runtime)):
    return {"settings": runtime.settings.all()}


@router.put("/api/admin/settings", dependencies=[Depends(require_admin)])
def admin_put_settings(data: dict = Depends(json_body), runtime=Depends(get_runtime)):
    try:
        result = runtime.settings.update(data)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "设置格式不正确: %s" % exc)
    runtime.worker.invalidate_prices()
    return {"settings": result}


@router.post("/api/admin/sync", dependencies=[Depends(require_admin)])
def admin_run_sync(runtime=Depends(get_runtime)):
    runtime.worker.reset_backoff()
    runtime.worker.invalidate_prices()
    runtime.worker.run_once()
    return {"sync": runtime.worker.state}
