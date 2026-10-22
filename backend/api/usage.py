"""Usage dashboards, history, CSV export and operational overview."""

import csv
import datetime
import io
import time

from fastapi import APIRouter, Depends, Request, Response

from api.dependencies import (
    get_connection,
    get_runtime,
    int_arg,
    pagination,
    query_arg,
    require_admin,
    require_user,
)
from services import accounts, usage
from services.billing import MICRO, epay_conf, money

router = APIRouter(tags=["usage"])


@router.get("/api/usage/summary")
def usage_summary(
    request: Request,
    user=Depends(require_user),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    days = int_arg(request, "days", 30, 1, 90)
    tz_offset = runtime.cfg.get("tz_offset_minutes")
    report = usage.summary(conn, user["id"], days, tz_offset)
    for field in ("today", "month", "range"):
        report[field]["cost"] = money(report[field]["cost"])
    return {
        "balance": money(user["balance_micro"]),
        "today": report["today"],
        "month": report["month"],
        "range": report["range"],
        "total": {"requests": report["total_requests"], "cost": money(user["total_spent_micro"])},
        "days": days,
        "daily": _daily_series(
            tz_offset,
            report["start"],
            days,
            report["daily"],
            {
                "requests": int,
                "cost": money,
                "tokens": int,
                "input_tokens": int,
                "output_tokens": int,
                "failed": int,
            },
        ),
        "by_model": [
            {
                "model": row["model"],
                "requests": row["requests"],
                "cost": money(row["cost"]),
                "tokens": row["tokens"] or 0,
            }
            for row in report["by_model"]
        ],
        "by_key": [
            {
                "key_id": row["key_id"],
                "name": row["name"] or "已删除密钥",
                "requests": row["requests"],
                "cost": money(row["cost"]),
            }
            for row in report["by_key"]
        ],
    }


@router.get("/api/usage/logs")
def usage_logs(request: Request, user=Depends(require_user), conn=Depends(get_connection)):
    return _logs_page(request, conn, user["id"])


@router.get("/api/admin/users/{user_id:int}/usage/logs", dependencies=[Depends(require_admin)])
def user_usage_logs(user_id: int, request: Request, conn=Depends(get_connection)):
    user = accounts.get(conn, user_id)
    return _logs_page(request, conn, user["id"])


@router.get("/api/usage/export", response_class=Response)
def usage_export(
    request: Request,
    user=Depends(require_user),
    conn=Depends(get_connection),
    runtime=Depends(get_runtime),
):
    rows = usage.export_logs(conn, user["id"], _filters(request))
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "时间",
            "密钥",
            "模型",
            "输入 tokens",
            "缓存读取 tokens",
            "缓存写入 tokens",
            "输出 tokens",
            "总 tokens",
            "费用",
            "状态",
            "耗时(ms)",
        ]
    )
    tz_offset = runtime.cfg.get("tz_offset_minutes")
    for row in rows:
        writer.writerow(
            [
                _time_label(row["ts"], tz_offset),
                row["key_name"] or "已删除密钥",
                row["model"],
                row["input_tokens"],
                row["cache_read_tokens"],
                row["cache_write_tokens"],
                row["output_tokens"],
                row["total_tokens"],
                "%.6f" % (row["cost_micro"] / MICRO),
                "失败" if row["failed"] else "成功",
                row["latency_ms"] if row["latency_ms"] is not None else "",
            ]
        )
    filename = "usage-%s.csv" % time.strftime("%Y%m%d-%H%M%S")
    return Response(
        ("\ufeff" + out.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="%s"' % filename,
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/admin/overview", dependencies=[Depends(require_admin)])
def overview(conn=Depends(get_connection), runtime=Depends(get_runtime)):
    tz_offset = runtime.cfg.get("tz_offset_minutes")
    report = usage.overview(conn, tz_offset)
    daily = _daily_series(
        tz_offset, report["start"], 14, report["daily"], {"requests": int, "cost": money}
    )
    recharges = _daily_series(
        tz_offset, report["start"], 14, report["recharge_daily"], {"recharge": money}
    )
    for item, extra in zip(daily, recharges):
        item["recharge"] = extra["recharge"]
    for item in report["usage"].values():
        item["cost"] = money(item["cost"])
    return {
        "users": {"total": report["users"]["total"], "today": report["users"]["today"]},
        "keys_active": report["keys_active"],
        "balance_total": money(report["users"]["balance_total_micro"]),
        "recharge": {name: money(value) for name, value in report["recharge"].items()},
        "usage": report["usage"],
        "daily": daily,
        "top_users": [
            {
                "id": row["id"],
                "username": row["username"],
                "requests": row["requests"],
                "cost": money(row["cost"]),
            }
            for row in report["top_users"]
        ],
        "unpriced_models": report["unpriced_models"],
        "sync": runtime.worker.state,
        "config": {
            "cpa_base_url": runtime.cpa.base,
            "cpa_configured": runtime.cpa.configured,
            "cpamp_usage_db": runtime.cfg["cpamp"].get("usage_db"),
            "online_payment": epay_conf(runtime.cfg) is not None,
        },
    }


def _filters(request):
    filters = {}
    for name in ("key_id", "start", "end"):
        if query_arg(request, name):
            filters[name] = int_arg(request, name, 0)
    for name in ("model", "status"):
        if query_arg(request, name):
            filters[name] = query_arg(request, name)
    return filters


def _logs_page(request, conn, user_id):
    page, size, offset = pagination(request)
    result = usage.list_logs(conn, user_id, _filters(request), size, offset)
    return {
        "items": [_usage_item(row) for row in result["items"]],
        "total": result["summary"]["n"],
        "sum_cost": money(result["summary"]["cost"]),
        "sum_tokens": result["summary"]["tokens"],
        "page": page,
        "page_size": size,
        "models": result["models"],
    }


def _usage_item(row):
    return {
        "id": row["id"],
        "ts": row["ts"],
        "key_id": row["key_id"],
        "key_name": row["key_name"] or "已删除密钥",
        "model": row["model"],
        "endpoint": row["endpoint"] or "",
        "input_tokens": row["input_tokens"],
        "cache_read_tokens": row["cache_read_tokens"],
        "cache_write_tokens": row["cache_write_tokens"],
        "output_tokens": row["output_tokens"],
        "reasoning_tokens": row["reasoning_tokens"],
        "total_tokens": row["total_tokens"],
        "cost": money(row["cost_micro"]),
        "failed": bool(row["failed"]),
        "latency_ms": row["latency_ms"],
        "stream": None if row["stream"] is None else bool(row["stream"]),
    }


def _time_label(ts, tz_offset_minutes, date_only=False):
    offset = int(tz_offset_minutes or 0) * 60000
    local = datetime.datetime.fromtimestamp((ts + offset) / 1000, tz=datetime.timezone.utc)
    return local.strftime("%Y-%m-%d" if date_only else "%Y-%m-%d %H:%M:%S")


def _daily_series(tz_offset_minutes, start, days, rows, fields):
    by_day = {row["d"]: row for row in rows}
    series = []
    for index in range(days):
        label = _time_label(start + index * usage.DAY_MS, tz_offset_minutes, date_only=True)
        row = by_day.get(label)
        item = {"date": label}
        for name, convert in fields.items():
            value = row[name] if row is not None and row[name] is not None else 0
            item[name] = convert(value)
        series.append(item)
    return series
