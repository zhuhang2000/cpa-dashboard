"""Configuration loading.

config.json provides the deployment settings. A handful of display/pricing
values can later be overridden from the admin page; those overrides live in the
database (see app.App.setting) and fall back to the values here.
"""
import copy
import json
import os

DEFAULTS = {
    "listen": "127.0.0.1",
    "port": 18400,
    "site_name": "API 控制台",
    # Unit shown for balances, prices and recharge amounts.
    "currency_symbol": "$",
    # Base URL users call with their API key, e.g. https://api.example.com
    "public_api_base": "",
    # Tutorial linked from the dashboard's quick-start card; empty hides the link.
    "guide_url": "https://help.tromino.wiki/guidance/api-guide#tool-intro",
    # Day boundaries for statistics. 480 = UTC+8 (Beijing time).
    "tz_offset_minutes": 480,
    "data_dir": "./data",
    "frontend_dir": "../frontend/dist",
    # Set true when running behind Nginx so X-Forwarded-For/Proto are honoured.
    "trust_proxy": False,
    # "auto" marks the session cookie Secure when the request arrived over HTTPS.
    "cookie_secure": "auto",
    "session_days": 7,
    "allow_register": True,
    "signup_bonus": 0,
    "max_keys_per_user": 10,
    # Keys are removed from CPA once the owner's balance is at or below this value.
    "min_balance_to_call": 0,
    "key_prefix": "sk-",
    "cpa": {
        "base_url": "http://127.0.0.1:8317",
        "management_key": "",
        "sync_keys": True,
        "timeout_seconds": 8,
    },
    "cpamp": {
        "usage_db": "/opt/services/cpa-manager-plus/data/usage.sqlite",
        "sync_interval_seconds": 15,
        "batch_size": 1000,
    },
    "pricing": {
        # Use CPA Manager Plus' synced official prices (USD / 1M tokens) for models
        # without a price set in the admin page, multiplied by cpamp_price_multiplier.
        "use_cpamp_prices": True,
        "cpamp_price_multiplier": 1.0,
        # Fallback price per 1M tokens for models that have no price anywhere. 0 = free.
        "default_input_price": 0,
        "default_output_price": 0,
        "bill_failed_requests": False,
    },
    "payment": {
        "presets": [10, 30, 50, 100, 200, 500],
        "min_amount": 1,
        "max_amount": 10000,
        # Balance credited per 1 unit of money paid online.
        "credit_ratio": 1.0,
        "epay": {
            "enabled": False,
            "gateway": "",
            "pid": "",
            "key": "",
            "channels": ["alipay", "wxpay"],
            # Public URL of this portal, used to build notify/return URLs.
            "site_url": "",
        },
    },
}

ENV_OVERRIDES = {
    "PORTAL_LISTEN": ("listen",),
    "PORTAL_PORT": ("port",),
    "PORTAL_CPA_BASE_URL": ("cpa", "base_url"),
    "PORTAL_CPA_MANAGEMENT_KEY": ("cpa", "management_key"),
    "PORTAL_CPAMP_USAGE_DB": ("cpamp", "usage_db"),
    "PORTAL_EPAY_KEY": ("payment", "epay", "key"),
}


def _merge(base, override):
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if path:
        path = os.path.abspath(path)
        with open(path, encoding="utf-8") as fh:
            _merge(cfg, json.load(fh))
        base_dir = os.path.dirname(path)

    for env_name, keys in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value is None:
            continue
        target = cfg
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = int(value) if keys == ("port",) else value

    for key in ("data_dir", "frontend_dir"):
        cfg[key] = os.path.normpath(os.path.join(base_dir, cfg[key]))
    usage_db = cfg["cpamp"].get("usage_db") or ""
    if usage_db and not os.path.isabs(usage_db):
        cfg["cpamp"]["usage_db"] = os.path.normpath(os.path.join(base_dir, usage_db))
    return cfg
