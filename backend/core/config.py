"""Directly load configuration from backend/core/.env."""

import os
import re
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = CORE_DIR / ".env"


def _read_env(path: Path) -> dict[str, str]:
    env = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def initialize_config(path: Path = CONFIG_PATH) -> bool:
    if path.exists():
        return False
    path.touch()
    return True


def _extra_nodes(env: dict[str, str], resolve) -> list[dict]:
    """Nodes after the first, declared as NODE<N>_CPA_BASE_URL / _CPA_MANAGEMENT_KEY / _CPAMP_USAGE_DB.

    CPA_BASE_URL, CPA_MANAGEMENT_KEY and CPAMP_USAGE_DB describe node 1, so numbering starts at 2.
    """
    numbers = sorted(
        int(match.group(1))
        for name in env
        if (match := re.fullmatch(r"NODE([1-9][0-9]*)_CPA_BASE_URL", name))
    )
    nodes = []
    for number in numbers:
        prefix = "NODE%d_" % number
        if number == 1:
            raise ValueError("1 号节点使用 CPA_BASE_URL 等配置，额外节点从 NODE2 开始编号")
        missing = [
            prefix + suffix
            for suffix in ("CPA_BASE_URL", "CPA_MANAGEMENT_KEY", "CPAMP_USAGE_DB")
            if not env.get(prefix + suffix)
        ]
        if missing:
            raise ValueError("节点 %d 缺少配置: %s" % (number, ", ".join(missing)))
        nodes.append(
            {
                "id": "node%d" % number,
                "cpa_base_url": env[prefix + "CPA_BASE_URL"],
                "management_key": env[prefix + "CPA_MANAGEMENT_KEY"],
                "usage_db": resolve(env[prefix + "CPAMP_USAGE_DB"]),
            }
        )
    return nodes


def load_config(config_path: Path | None = None) -> dict:
    path = Path(config_path) if config_path else CONFIG_PATH
    env = _read_env(path)
    base = path.parent

    def resolve(p: str) -> str:
        return os.path.normpath(os.path.join(base, p)) if p and not os.path.isabs(p) else p

    # Lower bounds that keep the usage sync from spinning (interval) or crawling (batch).
    interval = int(env["CPAMP_SYNC_INTERVAL_SECONDS"])
    batch_size = int(env["CPAMP_BATCH_SIZE"])
    if interval < 3:
        raise ValueError("CPAMP_SYNC_INTERVAL_SECONDS 不能小于 3")
    if batch_size < 100:
        raise ValueError("CPAMP_BATCH_SIZE 不能小于 100")
    # Online payment needs the gateway, merchant id and key as well as the switch.
    epay_enabled = env["EPAY_ENABLED"].lower() == "true" and all(
        env[name] for name in ("EPAY_GATEWAY", "EPAY_PID", "EPAY_KEY")
    )
    extra_nodes = _extra_nodes(env, resolve)
    usage_dbs = [resolve(env["CPAMP_USAGE_DB"])] + [node["usage_db"] for node in extra_nodes]
    if len(set(usage_dbs)) != len(usage_dbs):
        raise ValueError("每个 CPA 节点必须使用各自的 CPAMP 用量库")

    return {
        "listen": env["LISTEN"],
        "port": int(env["PORT"]),
        "site_name": env["SITE_NAME"],
        "currency_symbol": env["CURRENCY_SYMBOL"],
        "public_api_base": env["PUBLIC_API_BASE"],
        "tz_offset_minutes": int(env["TZ_OFFSET_MINUTES"]),
        "data_dir": resolve(env["DATA_DIR"]),
        "frontend_dir": resolve(env["FRONTEND_DIR"]),
        "trust_proxy": env["TRUST_PROXY"].lower() == "true",
        "cookie_secure": env["COOKIE_SECURE"],
        "session_days": int(env["SESSION_DAYS"]),
        "allow_register": env["ALLOW_REGISTER"].lower() == "true",
        "max_keys_per_user": int(env["MAX_KEYS_PER_USER"]),
        "min_balance_to_call": float(env["MIN_BALANCE_TO_CALL"]),
        "key_prefix": env["KEY_PREFIX"],
        "cpa": {
            "base_url": env["CPA_BASE_URL"],
            "management_key": env["CPA_MANAGEMENT_KEY"],
            "sync_keys": env["CPA_SYNC_KEYS"].lower() == "true",
            "timeout_seconds": float(env["CPA_TIMEOUT_SECONDS"]),
        },
        "cpamp": {
            "usage_db": resolve(env["CPAMP_USAGE_DB"]),
            "sync_interval_seconds": interval,
            "batch_size": batch_size,
        },
        "extra_nodes": extra_nodes,
        "pricing": {
            "use_cpamp_prices": env["USE_CPAMP_PRICES"].lower() == "true",
            "cpamp_price_discount": float(env["CPAMP_PRICE_DISCOUNT"]),
            "default_input_price": float(env["DEFAULT_INPUT_PRICE"]),
            "default_output_price": float(env["DEFAULT_OUTPUT_PRICE"]),
            "bill_failed_requests": env["BILL_FAILED_REQUESTS"].lower() == "true",
        },
        "payment": {
            "presets": [int(x) for x in env["PAYMENT_PRESETS"].split(",") if x.strip()],
            "min_amount": float(env["PAYMENT_MIN_AMOUNT"]),
            "max_amount": float(env["PAYMENT_MAX_AMOUNT"]),
            "credit_ratio": float(env["PAYMENT_CREDIT_RATIO"]),
            "epay": {
                "enabled": epay_enabled,
                "gateway": env["EPAY_GATEWAY"],
                "pid": env["EPAY_PID"],
                "key": env["EPAY_KEY"],
                "channels": [x.strip() for x in env["EPAY_CHANNELS"].split(",") if x.strip()],
                "site_url": env["EPAY_SITE_URL"],
            },
        },
    }
