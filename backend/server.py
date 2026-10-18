#!/usr/bin/env python3
"""API Portal server.

    python3 server.py                          # run (reads ./config.json if present)
    python3 server.py -c /path/config.json     # run with an explicit config
    python3 server.py create-admin <username>  # create an admin, or promote an existing user
    python3 server.py reset-password <username>
    python3 server.py gen-codes --amount 50 --count 10 [--batch name]
"""
import argparse
import getpass
import logging
import os
import signal
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portal import __version__  # noqa: E402
from portal.admin import register_routes as register_admin_routes  # noqa: E402
from portal.app import App  # noqa: E402
from portal.billing import apply_credit, to_micro  # noqa: E402
from portal.common import USERNAME_RE  # noqa: E402
from portal.config import load_config  # noqa: E402
from portal.constants import Role, TxType, UserStatus  # noqa: E402
from portal.db import now_ms, transaction  # noqa: E402
from portal.routes import register_routes  # noqa: E402
from portal.security import hash_password, new_redeem_code  # noqa: E402
from portal.web import Router, make_server  # noqa: E402

log = logging.getLogger("portal")


def _ask_password():
    while True:
        first = getpass.getpass("密码（至少 8 位）: ")
        if len(first) < 8:
            print("密码至少 8 位")
            continue
        if getpass.getpass("再次输入: ") != first:
            print("两次输入不一致")
            continue
        return first


def cmd_serve(app):
    router = Router()
    register_routes(router)
    register_admin_routes(router)
    server = make_server(app, router)
    app.worker.start()

    def shutdown(*_):
        log.info("shutting down")
        app.worker.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    host, port = server.server_address[:2]
    log.info("API Portal %s listening on http://%s:%s", __version__, host, port)
    log.info("frontend: %s", app.cfg["frontend_dir"])
    log.info("CPA management: %s (%s)", app.cpa.base or "-",
             "key sync on" if app.cpa.configured else "not configured, key sync off")
    log.info("CPAMP usage db: %s", app.cfg["cpamp"].get("usage_db") or "-")
    server.serve_forever()
    server.server_close()


def cmd_create_admin(app, username, password=None):
    if not USERNAME_RE.match(username):
        sys.exit("用户名需为 3-32 位字母、数字、下划线或短横线")
    conn = app.db()
    try:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            conn.execute("UPDATE users SET role = ?, status = ? WHERE id = ?",
                         (Role.ADMIN, UserStatus.ACTIVE, row["id"]))
            print("已将用户 %s 设为管理员" % username)
            return
        password = password or _ask_password()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), Role.ADMIN, now_ms()),
        )
        print("已创建管理员 %s" % username)
    finally:
        conn.close()


def cmd_reset_password(app, username, password=None):
    conn = app.db()
    try:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            sys.exit("用户不存在: %s" % username)
        password = password or _ask_password()
        with transaction(conn):
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (hash_password(password), row["id"]))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
        print("已重置 %s 的密码，并注销其所有登录" % username)
    finally:
        conn.close()


def cmd_gen_codes(app, amount, count, batch, expires_days):
    micro = to_micro(amount)
    if micro <= 0 or not 1 <= count <= 5000:
        sys.exit("面额需大于 0，数量 1-5000")
    expires_at = now_ms() + expires_days * 86400000 if expires_days else None
    conn = app.db()
    codes = []
    try:
        with transaction(conn):
            while len(codes) < count:
                code = new_redeem_code()
                if conn.execute(
                    "INSERT OR IGNORE INTO redeem_codes (code, amount_micro, batch, created_at, "
                    "expires_at) VALUES (?, ?, ?, ?, ?)",
                    (code, micro, batch, now_ms(), expires_at),
                ).rowcount:
                    codes.append(code)
    finally:
        conn.close()
    print("\n".join(codes))


def cmd_credit(app, username, amount, note):
    conn = app.db()
    try:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            sys.exit("用户不存在: %s" % username)
        with transaction(conn):
            balance = apply_credit(conn, row["id"], to_micro(amount), TxType.ADMIN, note=note or "命令行调整")
        print("%s 当前余额: %.4f" % (username, balance / 1e6))
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="API Portal (CPA user console)")
    parser.add_argument("-c", "--config", help="config.json path (default: ./config.json next to server.py)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("serve", help="run the HTTP server (default)")
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
    p = sub.add_parser("credit", help="adjust a user's balance (negative to deduct)")
    p.add_argument("username")
    p.add_argument("amount")
    p.add_argument("--note")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config_path = args.config
    if config_path is None:
        default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        config_path = default if os.path.exists(default) else None
    app = App(load_config(config_path))

    command = args.command or "serve"
    if command == "serve":
        cmd_serve(app)
    elif command == "create-admin":
        cmd_create_admin(app, args.username, args.password)
    elif command == "reset-password":
        cmd_reset_password(app, args.username, args.password)
    elif command == "gen-codes":
        cmd_gen_codes(app, args.amount, args.count, args.batch, args.expires_days)
    elif command == "credit":
        cmd_credit(app, args.username, args.amount, args.note)


if __name__ == "__main__":
    main()
