#!/usr/bin/env python3
"""自动管理 CLI Proxy 上游 Codex 凭证的额度禁用/恢复。

工作原理（无状态，每次检查都只看实时额度）:
  1. 通过 CPA v8 管理 API 获取所有凭证
  2. 对每个 Codex 凭证，通过 CPA 的 api-call 用它自己的 token 实时查询额度
     （chatgpt.com/backend-api/wham/usage，禁用中的凭证也能查）
  3. 额度用尽且启用中 → 禁用；额度可用且禁用中 → 启用；其余不动
  4. 查询失败的凭证本轮不做任何改动

注意: 启用/禁用完全由额度决定，手动禁用但仍有额度的凭证会在下一轮被重新启用。

用法:
  python3 quota-manager.py                # 单次运行
  python3 quota-manager.py --daemon       # 守护模式（循环运行）
  python3 quota-manager.py --interval 30  # 守护模式 + 自定义检查间隔（秒）
  python3 quota-manager.py --dry-run      # 只打印，不修改文件
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_INTERVAL = 60  # 默认检查间隔（秒）
DEFAULT_CPA_URL = "http://127.0.0.1:8317"
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
USER_AGENT = "codex_cli_rs/0.76.0 (Debian 13.0.0; x86_64) WindowsTerminal"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("quota-manager")

# ── CPA 管理 API ─────────────────────────────────────────────

def cpa_request(cpa_url, secret_key, path, body=None):
    """调用 CPA 管理 API，有 body 时用 POST，返回解析后的 JSON。"""
    req = urllib.request.Request(
        cpa_url.rstrip("/") + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method="POST" if body is not None else "GET",
    )
    req.add_header("Authorization", "Bearer " + secret_key)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_credentials(cpa_url, secret_key):
    """通过 v8 管理 API 获取所有凭证状态。"""
    try:
        return cpa_request(cpa_url, secret_key, "/v8/management/credentials").get("files", [])
    except (OSError, ValueError) as exc:
        log.error("无法连接 CPA 管理 API: %s", exc)
        return None


def fetch_rate_limit(cpa_url, secret_key, cred):
    """通过 CPA api-call 用该凭证的 token 实时查询 Codex 额度，返回 rate_limit，失败返回 None。"""
    try:
        resp = cpa_request(cpa_url, secret_key, "/v0/management/api-call", {
            "auth_index": cred.get("auth_index", ""),
            "method": "GET",
            "url": USAGE_URL,
            "header": {
                "Authorization": "Bearer $TOKEN$",
                "Chatgpt-Account-Id": (cred.get("id_token") or {}).get("chatgpt_account_id", ""),
                "User-Agent": USER_AGENT,
            },
        })
        if resp.get("status_code") != 200:
            raise ValueError("HTTP %s %s" % (resp.get("status_code"), str(resp.get("body"))[:200]))
        rate_limit = json.loads(resp.get("body") or "{}").get("rate_limit")
        if not isinstance(rate_limit, dict) or "allowed" not in rate_limit:
            raise ValueError("响应里没有 rate_limit.allowed")
        return rate_limit
    except (OSError, ValueError) as exc:
        log.warning("查询额度失败，本轮跳过: %s (%s): %s", cred.get("name"), cred.get("email", ""), exc)
        return None


def reset_time(rate_limit):
    """已用满的窗口里最晚的恢复时间，仅用于日志。"""
    windows = (rate_limit.get("primary_window"), rate_limit.get("secondary_window"))
    resets = [w.get("reset_at", 0) for w in windows if w and w.get("used_percent", 0) >= 100]
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(max(resets))) if resets else "未知"


# ── 凭证 JSON 文件操作 ───────────────────────────────────────

def set_disabled(path, disabled, dry_run=False):
    """修改凭证 JSON 的 disabled 字段。"""
    if dry_run:
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["disabled"] = disabled
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


# ── 主逻辑 ────────────────────────────────────────────────────

def check_and_manage(cpa_url, secret_key, dry_run=False):
    """一次检查：额度用尽的启用凭证 → 禁用；额度可用的禁用凭证 → 启用。"""
    credentials = fetch_credentials(cpa_url, secret_key)
    if credentials is None:
        return

    for cred in credentials:
        name = cred.get("name", "")
        path = cred.get("path", "")
        if cred.get("provider") != "codex" or not name or not path:
            continue
        rate_limit = fetch_rate_limit(cpa_url, secret_key, cred)
        if rate_limit is None:
            continue
        email = cred.get("email", "")
        disabled = cred.get("disabled", False)
        allowed = rate_limit["allowed"]
        log.debug("%s (%s): allowed=%s, disabled=%s", name, email, allowed, disabled)

        if not allowed and not disabled:
            log.info("🔴 额度耗尽，禁用凭证: %s (%s), 预计恢复时间: %s", name, email, reset_time(rate_limit))
            set_disabled(path, True, dry_run)
        elif allowed and disabled:
            log.info("🟢 额度已恢复，启用凭证: %s (%s)", name, email)
            set_disabled(path, False, dry_run)


def resolve_secret_key():
    """从 CPA config.yaml 或环境变量获取管理密钥。"""
    # 优先使用环境变量
    key = os.environ.get("CPA_SECRET_KEY", "").strip()
    if key:
        return key

    # 从 Portal .env 读取（它存的是明文密钥）
    portal_env = "/opt/services/api-portal/backend/core/.env"
    if os.path.exists(portal_env):
        try:
            with open(portal_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("CPA_MANAGEMENT_KEY="):
                        key = line.split("=", 1)[1].strip().strip("'\"")
                        if key:
                            return key
        except OSError:
            pass

    return ""


def main():
    parser = argparse.ArgumentParser(description="CLI Proxy 凭证额度自动禁用/恢复管理器")
    parser.add_argument("--daemon", action="store_true", help="守护模式，持续循环运行")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="检查间隔（秒），默认 %d" % DEFAULT_INTERVAL)
    parser.add_argument("--dry-run", action="store_true", help="只打印操作，不实际修改文件")
    parser.add_argument("--cpa-url", default=DEFAULT_CPA_URL, help="CPA 管理 API 地址")
    parser.add_argument("--secret-key", default="", help="CPA 管理密钥（也可通过 CPA_SECRET_KEY 环境变量设置）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示每个凭证的检查结果")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    secret_key = args.secret_key or resolve_secret_key()
    if not secret_key:
        log.error("未找到 CPA 管理密钥，请通过 --secret-key 或 CPA_SECRET_KEY 环境变量指定")
        sys.exit(1)

    if args.dry_run:
        log.info("DRY-RUN 模式：只打印操作，不修改任何文件")

    if not args.daemon:
        check_and_manage(args.cpa_url, secret_key, args.dry_run)
        return

    log.info("守护模式启动，检查间隔: %ds, CPA: %s", args.interval, args.cpa_url)
    while True:
        try:
            check_and_manage(args.cpa_url, secret_key, args.dry_run)
        except Exception:
            log.exception("检查异常")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
