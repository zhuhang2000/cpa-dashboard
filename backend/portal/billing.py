"""Money helpers, model pricing and the balance ledger.

Amounts are stored as integer micro-units (1 unit = 1_000_000 micro) so that
per-request costs of a fraction of a cent add up exactly.
"""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .constants import TxType
from .db import now_ms

MICRO = 1000000
PER_MILLION = 1000000.0
CACHE_READ_RATIO = 0.1
CACHE_WRITE_RATIO = 1.25


def to_micro(amount):
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid amount")
    if not value.is_finite():
        raise ValueError("invalid amount")
    return int((value * MICRO).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def from_micro(micro):
    return round((micro or 0) / MICRO, 6)


class Price:
    __slots__ = ("input", "output", "cache_read", "cache_write")

    def __init__(self, input_price, output_price, cache_read=None, cache_write=None):
        self.input = float(input_price or 0)
        self.output = float(output_price or 0)
        self.cache_read = self.input * CACHE_READ_RATIO if cache_read is None else float(cache_read)
        self.cache_write = self.input * CACHE_WRITE_RATIO if cache_write is None else float(cache_write)

    def scaled(self, factor):
        return Price(self.input * factor, self.output * factor,
                     self.cache_read * factor, self.cache_write * factor)

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
    for name in (model, model.lower(), re.sub(r"\(.*\)$", "", model).strip(),
                 model.rsplit("/", 1)[-1], model.rsplit("/", 1)[-1].lower()):
        if name and name not in seen:
            seen.append(name)
    return seen


def load_cpamp_prices(cpamp_conn):
    """Read CPA Manager Plus' synced official prices (USD per 1M tokens)."""
    prices = {}
    if cpamp_conn is None:
        return prices
    try:
        cols = {row[1] for row in cpamp_conn.execute("PRAGMA table_info(model_prices)")}
        if not {"model", "prompt_per_1m", "completion_per_1m"} <= cols:
            return prices
        wanted = ["cache_per_1m", "cache_read_per_1m", "cache_creation_per_1m",
                  "cache_read_configured", "cache_creation_configured"]
        select = ["model", "prompt_per_1m", "completion_per_1m"] + [
            c if c in cols else "0 AS " + c for c in wanted
        ]
        for row in cpamp_conn.execute("SELECT %s FROM model_prices" % ", ".join(select)):
            model, prompt, completion, cache, cache_read, cache_creation, cr_set, cc_set = row
            prompt = prompt or 0
            if cr_set or (cache_read or 0) > 0:
                read_price = cache_read or 0
            elif (cache or 0) > 0:
                read_price = cache
            else:
                read_price = prompt * CACHE_READ_RATIO
            write_price = cache_creation if (cc_set or (cache_creation or 0) > 0) else prompt * CACHE_WRITE_RATIO
            prices[model] = Price(prompt, completion or 0, read_price, write_price)
    except Exception:
        return {}
    return prices


class PriceBook:
    """Resolves the selling price of a model: admin override > CPAMP x multiplier > default."""

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
        """Return (Price or None, source) where source is override/cpamp/default/none."""
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
        overrides[row["model"]] = Price(row["input_price"], row["output_price"],
                                        row["cache_read_price"], row["cache_write_price"])
    return overrides


def build_price_book(conn, cpamp_prices, settings):
    default_in = float(settings("default_input_price") or 0)
    default_out = float(settings("default_output_price") or 0)
    default = Price(default_in, default_out) if (default_in > 0 or default_out > 0) else None
    return PriceBook(
        load_overrides(conn),
        cpamp_prices,
        settings("cpamp_price_multiplier"),
        default,
        use_cpamp=bool(settings("use_cpamp_prices")),
    )


def apply_credit(conn, user_id, amount_micro, tx_type, ref=None, note=None, operator_id=None):
    """Change a balance and write the ledger row. Call inside db.transaction()."""
    recharge = amount_micro if (tx_type in TxType.RECHARGE and amount_micro > 0) else 0
    conn.execute(
        "UPDATE users SET balance_micro = balance_micro + ?, "
        "total_recharge_micro = total_recharge_micro + ? WHERE id = ?",
        (amount_micro, recharge, user_id),
    )
    balance = conn.execute("SELECT balance_micro FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount_micro, balance_after_micro, ref, note, "
        "operator_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, tx_type, amount_micro, balance, ref, note, operator_id, now_ms()),
    )
    return balance
