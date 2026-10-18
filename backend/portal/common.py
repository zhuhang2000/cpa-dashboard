"""Helpers shared by the user and admin API modules."""
import datetime
import re

from .billing import from_micro, to_micro
from .db import now_ms
from .web import ApiError

DAY_MS = 86400000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,253}\.[^@\s.]{2,}$")


def money(micro):
    return from_micro(micro)


def tz_offset_ms(app):
    return int(app.cfg.get("tz_offset_minutes") or 0) * 60000


def day_start(app, ts):
    offset = tz_offset_ms(app)
    return ((ts + offset) // DAY_MS) * DAY_MS - offset


def month_start(app, ts):
    offset = tz_offset_ms(app)
    local = datetime.datetime.fromtimestamp((ts + offset) / 1000, tz=datetime.timezone.utc)
    first = datetime.datetime(local.year, local.month, 1, tzinfo=datetime.timezone.utc)
    return int(first.timestamp() * 1000) - offset


def day_label(app, ts):
    local = datetime.datetime.fromtimestamp((ts + tz_offset_ms(app)) / 1000, tz=datetime.timezone.utc)
    return local.strftime("%Y-%m-%d")


def time_label(app, ts):
    local = datetime.datetime.fromtimestamp((ts + tz_offset_ms(app)) / 1000, tz=datetime.timezone.utc)
    return local.strftime("%Y-%m-%d %H:%M:%S")


def daily_series(app, start, days, rows, fields):
    """Fill a {day: row} result into a dense list of `days` days starting at `start`."""
    by_day = {row["d"]: row for row in rows}
    series = []
    for i in range(days):
        label = day_label(app, start + i * DAY_MS)
        row = by_day.get(label)
        item = {"date": label}
        for name, convert in fields.items():
            value = row[name] if row is not None and row[name] is not None else 0
            item[name] = convert(value)
        series.append(item)
    return series


def parse_money(value, field="金额", minimum=None, maximum=None, allow_zero=False):
    if value is None or value == "":
        raise ApiError(400, "请填写%s" % field)
    try:
        micro = to_micro(value)
    except ValueError:
        raise ApiError(400, "%s格式不正确" % field)
    if micro == 0 and not allow_zero:
        raise ApiError(400, "%s不能为 0" % field)
    if minimum is not None and micro < to_micro(minimum):
        raise ApiError(400, "%s不能小于 %s" % (field, minimum))
    if maximum is not None and micro > to_micro(maximum):
        raise ApiError(400, "%s不能大于 %s" % (field, maximum))
    return micro


def parse_optional_ts(value, field):
    if value in (None, "", 0):
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "%s格式不正确" % field)
    if ts <= now_ms():
        raise ApiError(400, "%s必须是将来的时间" % field)
    return ts


def paginate(req, default_size=20, max_size=100):
    page = req.int_arg("page", 1, 1)
    size = req.int_arg("page_size", default_size, 1, max_size)
    return page, size, (page - 1) * size


def like_pattern(text):
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


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


def epay_conf(app):
    conf = app.cfg["payment"].get("epay") or {}
    if conf.get("enabled") and conf.get("gateway") and conf.get("pid") and conf.get("key"):
        return conf
    return None
