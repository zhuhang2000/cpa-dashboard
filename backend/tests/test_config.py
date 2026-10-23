"""Exercise the .env configuration loading without touching a real deployment."""

from pathlib import Path
import pytest

from core import config

SAMPLE_ENV = """
LISTEN=127.0.0.1
PORT=18400
SITE_NAME=API 控制台
CURRENCY_SYMBOL=$
PUBLIC_API_BASE=
TZ_OFFSET_MINUTES=480
DATA_DIR=../data
FRONTEND_DIR=../../frontend/dist
TRUST_PROXY=false
COOKIE_SECURE=auto
SESSION_DAYS=7
ALLOW_REGISTER=true
SIGNUP_BONUS=0
MAX_KEYS_PER_USER=10
MIN_BALANCE_TO_CALL=0
KEY_PREFIX=sk-
CPA_BASE_URL=http://127.0.0.1:8317
CPA_MANAGEMENT_KEY=
CPA_SYNC_KEYS=true
CPA_TIMEOUT_SECONDS=8
CPAMP_USAGE_DB=/opt/services/cpa-manager-plus/data/usage.sqlite
CPAMP_SYNC_INTERVAL_SECONDS=15
CPAMP_BATCH_SIZE=1000
USE_CPAMP_PRICES=true
CPAMP_PRICE_MULTIPLIER=1.0
DEFAULT_INPUT_PRICE=0
DEFAULT_OUTPUT_PRICE=0
BILL_FAILED_REQUESTS=false
PAYMENT_PRESETS=10,30,50,100,200,500
PAYMENT_MIN_AMOUNT=1
PAYMENT_MAX_AMOUNT=10000
PAYMENT_CREDIT_RATIO=1.0
EPAY_ENABLED=false
EPAY_GATEWAY=
EPAY_PID=
EPAY_KEY=
EPAY_CHANNELS=alipay,wxpay
EPAY_SITE_URL=
"""


@pytest.fixture(autouse=True)
def config_path(tmp_path, monkeypatch):
    path = tmp_path / "backend" / "core" / ".env"
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    return path


def test_loading_reads_env_values(config_path):
    config_path.write_text(SAMPLE_ENV)
    cfg = config.load_config(config_path)
    assert cfg["site_name"] == "API 控制台"
    assert cfg["port"] == 18400
    assert Path(cfg["data_dir"]) == config_path.parents[1] / "data"
    assert Path(cfg["frontend_dir"]) == config_path.parents[2] / "frontend" / "dist"


def test_loading_preserves_user_edits(config_path):
    text = SAMPLE_ENV.replace("SITE_NAME=API 控制台", "SITE_NAME=User configured site")
    text = text.replace("PORT=18400", "PORT=19000")
    text = text.replace("DEFAULT_INPUT_PRICE=0", "DEFAULT_INPUT_PRICE=2.5")
    config_path.write_text(text)

    cfg = config.load_config(config_path)
    assert cfg["site_name"] == "User configured site"
    assert cfg["port"] == 19000
    assert cfg["pricing"]["default_input_price"] == 2.5


def test_relative_paths_are_based_on_env_directory(config_path):
    text = SAMPLE_ENV.replace("DATA_DIR=../data", "DATA_DIR=./custom_state")
    text = text.replace("FRONTEND_DIR=../../frontend/dist", "FRONTEND_DIR=../custom_web/dist")
    text = text.replace(
        "CPAMP_USAGE_DB=/opt/services/cpa-manager-plus/data/usage.sqlite",
        "CPAMP_USAGE_DB=./ext/usage.sqlite",
    )
    config_path.write_text(text)

    cfg = config.load_config(config_path)
    assert Path(cfg["data_dir"]) == config_path.parent / "custom_state"
    assert Path(cfg["frontend_dir"]) == config_path.parents[1] / "custom_web" / "dist"
    assert Path(cfg["cpamp"]["usage_db"]) == config_path.parent / "ext" / "usage.sqlite"


def test_sync_settings_below_their_lower_bounds_are_refused(config_path):
    for old, new in (
        ("CPAMP_SYNC_INTERVAL_SECONDS=15", "CPAMP_SYNC_INTERVAL_SECONDS=2"),
        ("CPAMP_BATCH_SIZE=1000", "CPAMP_BATCH_SIZE=99"),
    ):
        config_path.write_text(SAMPLE_ENV.replace(old, new))
        with pytest.raises(ValueError):
            config.load_config(config_path)


def test_online_payment_needs_gateway_merchant_and_key(config_path):
    text = SAMPLE_ENV.replace("EPAY_ENABLED=false", "EPAY_ENABLED=true")
    config_path.write_text(text)
    assert config.load_config(config_path)["payment"]["epay"]["enabled"] is False
    text = text.replace("EPAY_GATEWAY=", "EPAY_GATEWAY=https://pay.example.test")
    text = text.replace("EPAY_PID=", "EPAY_PID=1001").replace("EPAY_KEY=", "EPAY_KEY=k")
    config_path.write_text(text)
    assert config.load_config(config_path)["payment"]["epay"]["enabled"] is True


def test_type_conversions(config_path):
    text = SAMPLE_ENV.replace("ALLOW_REGISTER=true", "ALLOW_REGISTER=false")
    text = text.replace("SIGNUP_BONUS=0", "SIGNUP_BONUS=10.5")
    text = text.replace("MAX_KEYS_PER_USER=10", "MAX_KEYS_PER_USER=20")
    text = text.replace("PAYMENT_PRESETS=10,30,50,100,200,500", "PAYMENT_PRESETS=5,15,50")
    text = text.replace("EPAY_CHANNELS=alipay,wxpay", "EPAY_CHANNELS=alipay")
    text = text.replace("TRUST_PROXY=false", "TRUST_PROXY=true")
    config_path.write_text(text)

    cfg = config.load_config(config_path)
    assert cfg["allow_register"] is False
    assert cfg["signup_bonus"] == 10.5
    assert cfg["max_keys_per_user"] == 20
    assert cfg["payment"]["presets"] == [5, 15, 50]
    assert cfg["payment"]["epay"]["channels"] == ["alipay"]
    assert cfg["trust_proxy"] is True
