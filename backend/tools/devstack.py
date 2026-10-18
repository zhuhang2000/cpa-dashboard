#!/usr/bin/env python3
"""Local development stack: fake CPA + fake CPA Manager Plus + fake EPay gateway.

    python3 tools/devstack.py run          # mock services on 127.0.0.1:18399 + traffic generator
    python3 tools/devstack.py seed-demo    # demo user with 30 days of history (run while `run` is up)

The mock CPA management API keeps an api-keys list. Every few seconds the
traffic generator writes fake requests for the keys in that list into a
CPAMP-shaped usage.sqlite, so the portal bills them exactly like production:
a key removed from CPA (balance 0, disabled, ...) stops producing traffic.
Never point this at real data.
"""

import argparse
import hashlib
import html
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
DATA = os.path.join(BACKEND, "data-dev")
CPAMP_DB = os.path.join(DATA, "cpamp", "usage.sqlite")
KEYS_FILE = os.path.join(DATA, "mock-cpa-keys.json")
MANAGEMENT_KEY = "dev-management-key"
EPAY_PID = "1001"
EPAY_KEY = "dev-epay-key"
OWN_KEY = "sk-operator-own-key-not-managed-by-portal"

# model: (prompt, completion, cache_read, cache_creation) USD per 1M tokens, None = unpriced
MODELS = {
    "gpt-5": (1.25, 10.0, 0.125, None),
    "gpt-5-mini": (0.25, 2.0, 0.025, None),
    "gpt-5-codex": (1.25, 10.0, 0.125, None),
    "claude-sonnet-4-5": (3.0, 15.0, 0.3, 3.75),
    "claude-opus-4-1": (15.0, 75.0, 1.5, 18.75),
    "gemini-2.5-pro": (1.25, 10.0, 0.31, None),
    "gemini-2.5-flash": (0.3, 2.5, 0.075, None),
    "internal-experimental": None,
}
WEIGHTS = [6, 8, 5, 6, 1, 3, 6, 1]

CPAMP_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    event_hash TEXT NOT NULL UNIQUE,
    timestamp_ms INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    provider TEXT,
    model TEXT NOT NULL,
    requested_model TEXT,
    endpoint TEXT,
    method TEXT,
    path TEXT,
    api_key_hash TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cache_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    normalized_uncached_input_tokens INTEGER,
    normalized_total_input_tokens INTEGER,
    normalized_cache_read_tokens INTEGER,
    normalized_cache_creation_tokens INTEGER,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    failed INTEGER NOT NULL DEFAULT 0,
    stream INTEGER,
    created_at_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS model_prices (
    model TEXT PRIMARY KEY,
    prompt_per_1m REAL NOT NULL,
    completion_per_1m REAL NOT NULL,
    cache_per_1m REAL NOT NULL,
    cache_read_per_1m REAL NOT NULL DEFAULT 0,
    cache_creation_per_1m REAL NOT NULL DEFAULT 0,
    prompt_configured INTEGER NOT NULL DEFAULT 0,
    completion_configured INTEGER NOT NULL DEFAULT 0,
    cache_read_configured INTEGER NOT NULL DEFAULT 0,
    cache_creation_configured INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    updated_at_ms INTEGER NOT NULL
);
"""


def cpamp_conn():
    os.makedirs(os.path.dirname(CPAMP_DB), exist_ok=True)
    conn = sqlite3.connect(CPAMP_DB, timeout=10)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(CPAMP_SCHEMA)
    now = int(time.time() * 1000)
    for model, price in MODELS.items():
        if price is None:
            continue
        prompt, completion, cache_read, cache_creation = price
        conn.execute(
            "INSERT OR REPLACE INTO model_prices (model, prompt_per_1m, completion_per_1m, cache_per_1m, "
            "cache_read_per_1m, cache_creation_per_1m, prompt_configured, completion_configured, "
            "cache_read_configured, cache_creation_configured, source, updated_at_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1, ?, 'mock', ?)",
            (
                model,
                prompt,
                completion,
                cache_read,
                cache_read,
                cache_creation or 0,
                1 if cache_creation else 0,
                now,
            ),
        )
    conn.commit()
    return conn


def fake_event(conn, api_key, ts_ms, model=None):
    model = model or random.choices(list(MODELS), WEIGHTS)[0]
    claude = model.startswith("claude")
    input_tokens = int(random.lognormvariate(8.3, 0.9))
    cache_read = int(input_tokens * random.choice([0, 0, 0.3, 0.6, 0.85]))
    cache_creation = int(input_tokens * 0.2) if claude and random.random() < 0.25 else 0
    uncached = max(input_tokens - cache_read - cache_creation, 0)
    output = int(random.lognormvariate(6.4, 0.9))
    reasoning = int(output * 0.4) if model.startswith("gpt-5") else 0
    failed = 1 if random.random() < 0.03 else 0
    if failed:
        uncached = cache_read = cache_creation = output = reasoning = 0
        input_tokens = 0
    endpoint = (
        "/v1/messages"
        if claude
        else ("/v1beta/models" if model.startswith("gemini") else "/v1/responses")
    )
    conn.execute(
        "INSERT INTO usage_events (request_id, event_hash, timestamp_ms, timestamp, provider, model, "
        "requested_model, endpoint, method, path, api_key_hash, input_tokens, output_tokens, "
        "reasoning_tokens, cached_tokens, cache_read_tokens, cache_creation_tokens, "
        "normalized_uncached_input_tokens, normalized_total_input_tokens, normalized_cache_read_tokens, "
        "normalized_cache_creation_tokens, total_tokens, latency_ms, failed, stream, created_at_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'POST', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            uuid.uuid4().hex,
            ts_ms,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_ms / 1000)),
            model.split("-")[0],
            model,
            model,
            endpoint,
            endpoint,
            hashlib.sha256(api_key.encode()).hexdigest(),
            input_tokens,
            output,
            reasoning,
            cache_read,
            cache_read,
            cache_creation,
            uncached,
            input_tokens,
            cache_read,
            cache_creation,
            input_tokens + output,
            random.randint(400, 30000) if not failed else 120,
            failed,
            random.choice([0, 1]),
            int(time.time() * 1000),
        ),
    )


# -- mock CPA management API + EPay gateway -----------------------------------------------
class KeyStore:
    def __init__(self):
        self.lock = threading.Lock()
        if os.path.exists(KEYS_FILE):
            with open(KEYS_FILE) as fh:
                self.keys = json.load(fh)
        else:
            self.keys = [OWN_KEY]
            self.save()

    def save(self):
        os.makedirs(DATA, exist_ok=True)
        with open(KEYS_FILE, "w") as fh:
            json.dump(self.keys, fh, indent=2)


def epay_sign(params, key):
    items = sorted(
        (k, str(v))
        for k, v in params.items()
        if k not in ("sign", "sign_type") and v is not None and str(v) != ""
    )
    return hashlib.md5(("&".join("%s=%s" % kv for kv in items) + key).encode()).hexdigest()


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write("[mock] %s\n" % (fmt % args))

        def _send(self, status, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _auth(self):
            if self.headers.get("Authorization") != "Bearer " + MANAGEMENT_KEY:
                self._send(401, {"error": "invalid management key"})
                return False
            return True

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length) if length else b""

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = {k: v[-1] for k, v in urllib.parse.parse_qs(url.query).items()}
            if url.path == "/v0/management/api-keys":
                if self._auth():
                    with store.lock:
                        self._send(200, {"api-keys": list(store.keys)})
            elif url.path == "/epay/submit.php":
                self._epay_page(query)
            else:
                self._send(404, {"error": "not found"})

        def do_PATCH(self):
            if self.path != "/v0/management/api-keys" or not self._auth():
                return
            body = json.loads(self._body() or b"{}")
            with store.lock:
                if body.get("old") in store.keys:
                    store.keys[store.keys.index(body["old"])] = body["new"]
                else:
                    store.keys.append(body["new"])
                store.save()
            self._send(200, {"status": "ok"})

        def do_PUT(self):
            if self.path != "/v0/management/api-keys" or not self._auth():
                return
            body = json.loads(self._body() or b"[]")
            keys = body if isinstance(body, list) else body.get("items") or []
            with store.lock:
                store.keys = [k for k in keys if isinstance(k, str)]
                store.save()
            sys.stderr.write("[mock] PUT api-keys (%d keys)\n" % len(store.keys))
            self._send(200, {"status": "ok"})

        def do_DELETE(self):
            url = urllib.parse.urlsplit(self.path)
            if url.path != "/v0/management/api-keys" or not self._auth():
                return
            value = urllib.parse.parse_qs(url.query).get("value", [""])[0].strip()
            with store.lock:
                store.keys = [k for k in store.keys if k.strip() != value]
                store.save()
            self._send(200, {"status": "ok"})

        def do_POST(self):
            if self.path == "/epay/pay":
                form = {k: v[-1] for k, v in urllib.parse.parse_qs(self._body().decode()).items()}
                self._epay_pay(form)
            else:
                self._send(404, {"error": "not found"})

        # Fake EPay: shows a confirm page, then calls notify_url and redirects to return_url.
        def _epay_page(self, query):
            ok = query.get("pid") == EPAY_PID and query.get("sign") == epay_sign(query, EPAY_KEY)
            if not ok:
                self._send(400, "签名错误".encode(), "text/plain; charset=utf-8")
                return
            hidden = "".join(
                '<input type="hidden" name="%s" value="%s">' % (html.escape(k), html.escape(v))
                for k, v in query.items()
            )
            page = """<!doctype html><meta charset="utf-8"><title>模拟收银台</title>
<body style="font-family:system-ui;max-width:420px;margin:80px auto;text-align:center">
<h2>模拟收银台（仅本地开发）</h2><p>%s</p><p style="font-size:32px;font-weight:700">¥%s</p>
<p>支付方式：%s</p><form method="post" action="/epay/pay">%s
<button style="padding:10px 28px;font-size:16px">确认支付</button></form></body>""" % (
                html.escape(query.get("name", "")),
                html.escape(query.get("money", "")),
                html.escape(query.get("type", "")),
                hidden,
            )
            self._send(200, page.encode(), "text/html; charset=utf-8")

        def _epay_pay(self, form):
            params = {
                "pid": EPAY_PID,
                "trade_no": "MOCK" + uuid.uuid4().hex[:16],
                "out_trade_no": form.get("out_trade_no", ""),
                "type": form.get("type", ""),
                "name": form.get("name", ""),
                "money": form.get("money", ""),
                "trade_status": "TRADE_SUCCESS",
            }
            params["sign"] = epay_sign(params, EPAY_KEY)
            params["sign_type"] = "MD5"
            query = urllib.parse.urlencode(params)
            try:
                with urllib.request.urlopen(form["notify_url"] + "?" + query, timeout=5) as resp:
                    sys.stderr.write("[mock] notify -> %s\n" % resp.read().decode())
            except Exception as exc:
                sys.stderr.write("[mock] notify failed: %s\n" % exc)
            self.send_response(302)
            self.send_header("Location", form["return_url"] + "?" + query)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def traffic_loop(store, interval):
    conn = cpamp_conn()
    while True:
        with store.lock:
            keys = list(store.keys)
        now = int(time.time() * 1000)
        for key in keys:
            if random.random() < 0.6:
                for _ in range(random.randint(1, 2)):
                    fake_event(conn, key, now - random.randint(0, 2000))
        conn.commit()
        time.sleep(interval)


def cmd_run(args):
    store = KeyStore()
    cpamp_conn().close()
    threading.Thread(target=traffic_loop, args=(store, args.interval), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(store))
    print(
        "mock CPA management API : http://127.0.0.1:%d/v0/management (key: %s)"
        % (args.port, MANAGEMENT_KEY)
    )
    print(
        "mock EPay gateway       : http://127.0.0.1:%d/epay (pid %s, key %s)"
        % (args.port, EPAY_PID, EPAY_KEY)
    )
    print("mock CPAMP usage db     : %s" % CPAMP_DB)
    server.serve_forever()


def cmd_seed_demo(args):
    """Create demo/demo12345 with two keys and 30 days of billed history."""
    sys.path.insert(0, BACKEND)
    from core.db import init_db, transaction
    from core.security import hash_password, new_api_key, sha256_hex
    from services.billing import apply_credit, to_micro

    portal_db = os.path.join(DATA, "portal.sqlite")
    init_db(portal_db)
    conn = sqlite3.connect(portal_db, isolation_level=None)
    conn.row_factory = sqlite3.Row
    now = int(time.time() * 1000)
    created = now - 31 * 86400000
    row = conn.execute("SELECT id FROM users WHERE username = 'demo'").fetchone()
    if row:
        sys.exit("demo 用户已存在，跳过（删除 backend/data-dev 可重置开发数据）")
    with transaction(conn):
        uid = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("demo", "demo@example.com", hash_password("demo12345"), created),
        ).lastrowid
        apply_credit(
            conn, uid, to_micro(200), "redeem", ref="DEMO-SEED-CODE-0001", note="兑换码充值"
        )
        keys = []
        for name in ("生产环境", "本地开发"):
            key = new_api_key()
            conn.execute(
                "INSERT INTO api_keys (user_id, name, key, key_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (uid, name, key, sha256_hex(key), created),
            )
            keys.append(key)
    src = cpamp_conn()
    for day in range(30, -1, -1):
        for _ in range(random.randint(8, 40)):
            ts = now - day * 86400000 - random.randint(0, 86400000)
            if ts < now:
                fake_event(src, random.choice(keys), ts)
    src.commit()
    print(
        "已创建 demo / demo12345（余额 200，两个密钥，30 天调用记录）。等待一个同步周期后即可看到账单。"
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--port", type=int, default=18399)
    p.add_argument("--interval", type=float, default=4.0)
    sub.add_parser("seed-demo")
    args = parser.parse_args()
    {"run": cmd_run, "seed-demo": cmd_seed_demo}[args.command](args)


if __name__ == "__main__":
    main()
