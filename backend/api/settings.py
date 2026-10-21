"""Public site information and administrator runtime settings/sync actions."""

from fastapi import APIRouter, Depends

from api.dependencies import get_connection, get_runtime, json_body, require_admin
from core.constants import VERSION
from core.errors import ApiError
from services.api_keys import max_keys
from services.billing import epay_conf
from services.notices import latest_at

router = APIRouter(tags=["settings"])


@router.get("/api/status")
def get_status(runtime=Depends(get_runtime), conn=Depends(get_connection)):
    cfg, settings = runtime.cfg, runtime.settings
    pay, conf = cfg["payment"], epay_conf(cfg)
    return {
        "site_name": settings.get("site_name"),
        "public_api_base": settings.get("public_api_base"),
        "guide_url": cfg["guide_url"],
        "announcement": settings.get("announcement"),
        "notice_latest_at": latest_at(conn),
        "allow_register": bool(settings.get("allow_register")),
        "signup_bonus": settings.get("signup_bonus"),
        "currency_symbol": cfg["currency_symbol"],
        "max_keys_per_user": max_keys(cfg),
        "payment": {
            "online": conf is not None,
            "channels": list(conf.get("channels") or []) if conf else [],
            "presets": pay.get("presets") or [],
            "min_amount": pay.get("min_amount"),
            "max_amount": pay.get("max_amount"),
            "credit_ratio": pay.get("credit_ratio") or 1,
        },
        "version": VERSION,
    }


@router.get("/api/admin/settings", dependencies=[Depends(require_admin)])
def get_settings(runtime=Depends(get_runtime)):
    return {"settings": runtime.settings.all()}


@router.put("/api/admin/settings", dependencies=[Depends(require_admin)])
def put_settings(data: dict = Depends(json_body), runtime=Depends(get_runtime)):
    try:
        result = runtime.settings.update(data)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "设置格式不正确: %s" % exc)
    runtime.worker.invalidate_prices()
    return {"settings": result}


@router.post("/api/admin/sync", dependencies=[Depends(require_admin)])
def run_sync(runtime=Depends(get_runtime)):
    runtime.worker.reset_backoff()
    runtime.worker.invalidate_prices()
    runtime.worker.run_once()
    return {"sync": runtime.worker.state}
