"""Model prices, pricing rules and the catalog shown to users and administrators."""

import re

from core.db import get_setting, now_ms, set_setting, transaction
from core.errors import ApiError

MICRO = 1000000
PER_MILLION = 1000000.0
CACHE_READ_RATIO = 0.1
CACHE_WRITE_RATIO = 1.25
DAY_MS = 86400000


# ---- Shared ----


class Price:
    __slots__ = ("input", "output", "cache_read", "cache_write")

    def __init__(self, input_price, output_price, cache_read=None, cache_write=None):
        self.input = float(input_price or 0)
        self.output = float(output_price or 0)
        self.cache_read = self.input * CACHE_READ_RATIO if cache_read is None else float(cache_read)
        self.cache_write = (
            self.input * CACHE_WRITE_RATIO if cache_write is None else float(cache_write)
        )

    def scaled(self, factor):
        return Price(
            self.input * factor,
            self.output * factor,
            self.cache_read * factor,
            self.cache_write * factor,
        )

    def as_dict(self):
        return {
            "input": round(self.input, 6),
            "output": round(self.output, 6),
            "cache_read": round(self.cache_read, 6),
            "cache_write": round(self.cache_write, 6),
        }

    def cost_micro(self, uncached_input, cache_read, cache_write, output):
        cost = (
            uncached_input * self.input
            + cache_read * self.cache_read
            + cache_write * self.cache_write
            + output * self.output
        ) / PER_MILLION
        return int(round(cost * MICRO))


def _model_candidates(model):
    seen = []
    for name in (
        model,
        model.lower(),
        re.sub(r"\(.*\)$", "", model).strip(),
        model.rsplit("/", 1)[-1],
        model.rsplit("/", 1)[-1].lower(),
    ):
        if name and name not in seen:
            seen.append(name)
    return seen


class PriceBook:
    """Resolve selling prices: admin override > external price x multiplier > default."""

    def __init__(self, overrides, cpamp_prices, multiplier, default_price, use_cpamp=True):
        self.overrides = overrides
        self.cpamp = cpamp_prices if use_cpamp else {}
        self.cpamp_lower = {k.lower(): v for k, v in self.cpamp.items()}
        self.multiplier = float(multiplier or 0)
        self.default = default_price

    def cpamp_price(self, model):
        for name in _model_candidates(model):
            price = self.cpamp.get(name) or self.cpamp_lower.get(name.lower())
            if price is not None:
                return price.scaled(self.multiplier)
        return None

    def resolve(self, model):
        """Return (Price or None, source), with source override/cpamp/default/none."""
        override = self.overrides.get(model)
        if override is not None:
            return override, "override"
        price = self.cpamp_price(model)
        if price is not None:
            return price, "cpamp"
        if self.default is not None:
            return self.default, "default"
        return None, "none"


def load_overrides(conn):
    overrides = {}
    for row in conn.execute("SELECT * FROM model_prices"):
        overrides[row["model"]] = Price(
            row["input_price"],
            row["output_price"],
            row["cache_read_price"],
            row["cache_write_price"],
        )
    return overrides


def build_price_book(conn, cpamp_prices, setting):
    default_in = float(setting("default_input_price") or 0)
    default_out = float(setting("default_output_price") or 0)
    default = Price(default_in, default_out) if (default_in > 0 or default_out > 0) else None
    return PriceBook(
        load_overrides(conn),
        cpamp_prices,
        setting("cpamp_price_multiplier"),
        default,
        use_cpamp=bool(setting("use_cpamp_prices")),
    )


# ---- User operations ----


def list_prices(conn, cpamp_prices, setting, currency_symbol):
    book = build_price_book(conn, cpamp_prices, setting)
    notes = {
        row["model"]: row["note"] for row in conn.execute("SELECT model, note FROM model_prices")
    }
    hidden = set(get_setting(conn, "hidden_models", []) or [])
    since = now_ms() - 30 * DAY_MS
    models = set(notes) | set(cpamp_prices)
    models.update(
        row[0]
        for row in conn.execute(
            "SELECT model FROM seen_models WHERE last_seen_ms >= ? AND model != 'unknown'", (since,)
        )
    )
    items = []
    for model in sorted(models, key=str.lower):
        if model in hidden:
            continue
        price, source = book.resolve(model)
        if price is None:
            continue
        item = price.as_dict()
        item.update(model=model, note=notes.get(model) or "", source=source)
        items.append(item)
    return {"items": items, "currency_symbol": currency_symbol}


# ---- Administrator operations ----


def admin_list_prices(conn, cpamp_prices, setting):
    book = build_price_book(conn, cpamp_prices, setting)
    reference = PriceBook({}, cpamp_prices, 1.0, None)
    overrides = {r["model"]: r for r in conn.execute("SELECT * FROM model_prices")}
    seen = {r["model"]: r for r in conn.execute("SELECT * FROM seen_models")}
    hidden = set(get_setting(conn, "hidden_models", []) or [])
    items = []
    for model in sorted(set(overrides) | set(seen) | set(cpamp_prices), key=str.lower):
        price, source = book.resolve(model)
        ref = reference.cpamp_price(model)
        override = overrides.get(model)
        usage = seen.get(model)
        items.append(
            {
                "model": model,
                "source": source,
                "price": price.as_dict() if price else None,
                "cpamp": ref.as_dict() if ref else None,
                "override": None
                if override is None
                else {
                    "input": override["input_price"],
                    "output": override["output_price"],
                    "cache_read": override["cache_read_price"],
                    "cache_write": override["cache_write_price"],
                    "note": override["note"] or "",
                },
                "hidden": model in hidden,
                "last_seen_ms": usage["last_seen_ms"] if usage else None,
                "calls": usage["calls"] if usage else 0,
            }
        )
    return {"items": items, "cpamp_models": len(cpamp_prices)}


def _price_value(data, name, label, optional=False):
    value = data.get(name)
    if value in (None, ""):
        if optional:
            return None
        raise ApiError(400, "请填写%s" % label)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "%s格式不正确" % label)
    if number < 0 or number != number or number > 1e6:
        raise ApiError(400, "%s超出范围" % label)
    return number


def upsert_price(conn, data):
    model = str(data.get("model") or "").strip()
    if not model or len(model) > 128:
        raise ApiError(400, "模型名称需为 1-128 个字符")
    values = (
        _price_value(data, "input", "输入价格"),
        _price_value(data, "output", "输出价格"),
        _price_value(data, "cache_read", "缓存读取价格", optional=True),
        _price_value(data, "cache_write", "缓存写入价格", optional=True),
        str(data.get("note") or "").strip()[:100] or None,
    )
    with transaction(conn):
        conn.execute(
            "INSERT OR IGNORE INTO model_prices (model, updated_at) VALUES (?, ?)",
            (model, now_ms()),
        )
        conn.execute(
            "UPDATE model_prices SET input_price = ?, output_price = ?, cache_read_price = ?, "
            "cache_write_price = ?, note = ?, updated_at = ? WHERE model = ?",
            values + (now_ms(), model),
        )
    return {"ok": True}


def delete_price(conn, model):
    conn.execute("DELETE FROM model_prices WHERE model = ?", (model,))
    return {"ok": True}


def set_visibility(conn, data):
    model = str(data.get("model") or "").strip()
    if not model:
        raise ApiError(400, "缺少模型名称")
    with transaction(conn):
        hidden = set(get_setting(conn, "hidden_models", []) or [])
        if data.get("hidden"):
            hidden.add(model)
        else:
            hidden.discard(model)
        set_setting(conn, "hidden_models", sorted(hidden))
    return {"ok": True}


# ---- Sync worker and CLI ----


def prices_from_external(raw):
    """Convert adapter records into prices without opening the external database."""
    return {
        model: Price(value["input"], value["output"], value["cache_read"], value["cache_write"])
        for model, value in raw.items()
    }


def touch_model(conn, model, last_ms, calls):
    """Record model sightings inside the caller's usage-sync transaction."""
    if not model:
        return
    conn.execute(
        "INSERT OR IGNORE INTO seen_models (model, last_seen_ms, calls) VALUES (?, ?, 0)",
        (model, last_ms or 0),
    )
    conn.execute(
        "UPDATE seen_models SET last_seen_ms = MAX(last_seen_ms, ?), calls = calls + ? "
        "WHERE model = ?",
        (last_ms or 0, calls, model),
    )
