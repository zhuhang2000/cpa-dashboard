"""Command-line parsing and output; business operations live in services."""

import argparse
import getpass
import logging
import sys

import uvicorn

from core.config import CONFIG_PATH, initialize_config, load_config
from core.constants import VERSION, RedeemType
from core.errors import ApiError
from runtime.app import Runtime, create_app
from services import accounts, billing

log = logging.getLogger("portal")


def _ask_password():
    while True:
        first = getpass.getpass("密码（至少 8 位）: ")
        if getpass.getpass("再次输入: ") == first:
            return first
        print("两次输入不一致")


def cmd_serve(runtime):
    host = runtime.cfg["listen"]
    port = runtime.cfg["port"]
    log.info("API Portal %s listening on http://%s:%s", VERSION, host, port)
    log.info("frontend: %s", runtime.cfg["frontend_dir"])
    log.info(
        "CPA management: %s (%s)",
        runtime.cpa.base or "-",
        "key sync on" if runtime.cpa.configured else "not configured, key sync off",
    )
    log.info("CPAMP usage db: %s", runtime.cfg["cpamp"]["usage_db"] or "-")
    # Exactly one process owns the embedded sync worker and in-memory limits.
    # Proxy headers are interpreted by our request dependency according to config.
    uvicorn.run(
        create_app(runtime=runtime),
        host=host,
        port=port,
        workers=1,
        proxy_headers=False,
        server_header=False,
        timeout_keep_alive=30,
    )


def cmd_create_admin(runtime, username, password=None):
    conn = runtime.db()
    try:
        if not accounts.find_by_username(conn, username):
            password = password or _ask_password()
        _, created = accounts.create_admin(conn, username, password)
    except ApiError as exc:
        sys.exit(exc.message)
    finally:
        conn.close()
    print("已创建管理员 %s" % username if created else "已将用户 %s 设为管理员" % username)


def cmd_reset_password(runtime, username, password=None):
    conn = runtime.db()
    try:
        row = accounts.find_by_username(conn, username)
        if row is None:
            sys.exit("用户不存在: %s" % username)
        accounts.reset_password(conn, row["id"], password or _ask_password())
    except ApiError as exc:
        sys.exit(exc.message)
    finally:
        conn.close()
    print("已重置 %s 的密码，并注销其所有登录" % username)


def cmd_gen_codes(runtime, amount, count, batch, expires_days, code_type):
    data = {
        "amount": amount,
        "count": count,
        "batch": batch,
        "expires_days": expires_days,
        "type": code_type,
    }
    conn = runtime.db()
    try:
        codes = billing.create_codes(conn, None, data)["codes"]
    except ApiError as exc:
        sys.exit(exc.message)
    finally:
        conn.close()
    print("\n".join(codes))


def cmd_credit(runtime, username, amount, note):
    conn = runtime.db()
    try:
        row = accounts.find_by_username(conn, username)
        if row is None:
            sys.exit("用户不存在: %s" % username)
        # A positive amount is recorded as a recharge, like an offline payment.
        data = {"amount": amount, "type": RedeemType.RECHARGE, "note": note or "命令行调整"}
        balance = billing.adjust_balance(conn, row["id"], None, data)["balance"]
    except ApiError as exc:
        sys.exit(exc.message)
    finally:
        conn.close()
    print("%s 当前余额: %.4f" % (username, balance))


def main():
    parser = argparse.ArgumentParser(description="API Portal (CPA user console)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="run the HTTP server (default)")
    sub.add_parser("init-config", help="create config/config.json if missing, then exit")
    p = sub.add_parser("create-admin", help="create an admin or promote an existing user")
    p.add_argument("username")
    p.add_argument("--password", help="non-interactive password (avoid on shared shells)")
    p = sub.add_parser("reset-password", help="reset a user's password")
    p.add_argument("username")
    p.add_argument("--password")
    p = sub.add_parser("gen-codes", help="generate redeem codes")
    p.add_argument("--amount", required=True)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--batch")
    p.add_argument("--expires-days", type=int, default=0)
    p.add_argument(
        "--type",
        choices=RedeemType.ALL,
        default=RedeemType.RECHARGE,
        help="recharge counts toward recharge totals; gift only adds balance",
    )
    p = sub.add_parser("credit", help="adjust a user's balance (negative to deduct)")
    p.add_argument("username")
    p.add_argument("amount")
    p.add_argument("--note")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    command = args.command or "serve"
    try:
        if command == "init-config":
            created = initialize_config()
            print(f"{'已生成配置' if created else '配置已存在，保留原内容'}: {CONFIG_PATH}")
            return
        cfg = load_config()
    except (OSError, ValueError) as exc:
        sys.exit(f"配置错误（{CONFIG_PATH}）: {exc}")
    app = Runtime(cfg)

    if command == "serve":
        cmd_serve(app)
    elif command == "create-admin":
        cmd_create_admin(app, args.username, args.password)
    elif command == "reset-password":
        cmd_reset_password(app, args.username, args.password)
    elif command == "gen-codes":
        cmd_gen_codes(app, args.amount, args.count, args.batch, args.expires_days, args.type)
    elif command == "credit":
        cmd_credit(app, args.username, args.amount, args.note)
