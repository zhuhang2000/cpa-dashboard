"""HTTP layer: a small JSON router and static file server on top of http.server."""
import gzip
import json
import logging
import mimetypes
import os
import re
import socket
import threading
import time
import urllib.parse
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .db import now_ms
from .security import sha256_hex

log = logging.getLogger("portal.http")

MAX_BODY = 1 << 20
SESSION_COOKIE = "portal_sid"
DAY_MS = 86400000
COMPRESSIBLE = (".js", ".css", ".html", ".svg", ".json", ".txt", ".map")
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; font-src 'self' data:; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'"
)

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("font/woff2", ".woff2")


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Response:
    def __init__(self, body=b"", status=200, content_type="application/json; charset=utf-8",
                 headers=None):
        self.body = body
        self.status = status
        self.headers = [("Content-Type", content_type)] + list(headers or [])

    @classmethod
    def json(cls, data, status=200):
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return cls(body, status, headers=[("Cache-Control", "no-store")])

    @classmethod
    def text(cls, text, status=200):
        return cls(text.encode("utf-8"), status, "text/plain; charset=utf-8",
                   [("Cache-Control", "no-store")])

    @classmethod
    def redirect(cls, location):
        return cls(b"", 302, "text/plain; charset=utf-8", [("Location", location)])


class Request:
    def __init__(self, handler, app, method, path, query, body, params):
        self.app = app
        self.method = method
        self.path = path
        self.query = query
        self.body = body
        self.params = params
        self.headers = handler.headers
        self.ip = _client_ip(handler, app.cfg.get("trust_proxy"))
        self.user = None
        self.session_hash = None
        self.cookies_out = []
        self._json = None
        self._conn = None

    # -- helpers -------------------------------------------------------------------
    @property
    def conn(self):
        if self._conn is None:
            self._conn = self.app.db()
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def json(self):
        if self._json is None:
            if not self.body:
                self._json = {}
            else:
                try:
                    self._json = json.loads(self.body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    raise ApiError(400, "请求体不是合法的 JSON")
            if not isinstance(self._json, dict):
                raise ApiError(400, "请求体必须是 JSON 对象")
        return self._json

    def arg(self, name, default=None):
        value = self.query.get(name)
        return default if value in (None, "") else value

    def int_arg(self, name, default, low=None, high=None):
        try:
            value = int(self.arg(name, default))
        except (TypeError, ValueError):
            raise ApiError(400, "参数 %s 必须是整数" % name)
        if low is not None:
            value = max(low, value)
        if high is not None:
            value = min(high, value)
        return value

    def host(self):
        if self.app.cfg.get("trust_proxy") and self.headers.get("X-Forwarded-Host"):
            return self.headers["X-Forwarded-Host"].split(",")[0].strip()
        return (self.headers.get("Host") or "").strip()

    def is_https(self):
        if self.app.cfg.get("trust_proxy"):
            proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
            return proto == "https"
        return False

    def origin_url(self):
        return ("https://" if self.is_https() else "http://") + self.host()

    def cookie(self, name):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        jar = SimpleCookie()
        try:
            jar.load(raw)
        except CookieError:
            return None
        morsel = jar.get(name)
        return morsel.value if morsel else None

    def set_cookie(self, name, value, max_age):
        secure_conf = self.app.cfg.get("cookie_secure", "auto")
        secure = self.is_https() if secure_conf == "auto" else bool(secure_conf)
        parts = ["%s=%s" % (name, value), "Path=/", "HttpOnly", "SameSite=Lax",
                 "Max-Age=%d" % max_age]
        if secure:
            parts.append("Secure")
        self.cookies_out.append("; ".join(parts))

    def clear_cookie(self, name):
        self.cookies_out.append("%s=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0" % name)

    # -- auth ----------------------------------------------------------------------
    def authenticate(self, required):
        token = self.cookie(SESSION_COOKIE)
        if token:
            token_hash = sha256_hex(token)
            row = self.conn.execute(
                "SELECT u.*, s.expires_at AS session_expires_at FROM sessions s "
                "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
                (token_hash,),
            ).fetchone()
            now = now_ms()
            if row is not None and row["session_expires_at"] > now and row["status"] == "active":
                self.user = row
                self.session_hash = token_hash
                lifetime = int(self.app.cfg.get("session_days") or 7) * DAY_MS
                if row["session_expires_at"] - now < lifetime // 2:  # sliding renewal
                    self.conn.execute("UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
                                      (now + lifetime, token_hash))
                    self.set_cookie(SESSION_COOKIE, token, lifetime // 1000)
        if required and self.user is None:
            raise ApiError(401, "请先登录")
        if required == "admin" and self.user["role"] != "admin":
            raise ApiError(403, "需要管理员权限")


def _client_ip(handler, trust_proxy):
    if trust_proxy:
        real_ip = handler.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        forwarded = handler.headers.get("X-Forwarded-For")
        if forwarded:
            # The right-most entry is the one appended by our own reverse proxy.
            return forwarded.split(",")[-1].strip()
    return handler.client_address[0]


class Router:
    def __init__(self):
        self.routes = []

    def add(self, method, pattern, handler, auth="user", raw=False):
        ints = set()

        def repl(match):
            if match.group(1):
                ints.add(match.group(2))
                return r"(?P<%s>\d+)" % match.group(2)
            return r"(?P<%s>[^/]+)" % match.group(2)

        regex = re.compile("^" + re.sub(r"<(int:)?(\w+)>", repl, pattern) + "$")
        self.routes.append((method, regex, handler, auth, raw, ints))

    def match(self, method, path):
        method_mismatch = False
        for route_method, regex, handler, auth, raw, ints in self.routes:
            found = regex.match(path)
            if not found:
                continue
            if route_method != method:
                method_mismatch = True
                continue
            params = found.groupdict()
            for name in ints:
                params[name] = int(params[name])
            return handler, params, auth, raw
        if method_mismatch:
            raise ApiError(405, "不支持的请求方法")
        raise ApiError(404, "接口不存在")


class StaticFiles:
    def __init__(self, root):
        self.root = os.path.realpath(root)
        self._gzip_cache = {}
        self._lock = threading.Lock()

    def resolve(self, path):
        """Return the file to serve for a URL path, or None for a 404."""
        rel = path.lstrip("/")
        if "\x00" in rel:
            return None
        full = os.path.realpath(os.path.join(self.root, rel))
        if full != self.root and not full.startswith(self.root + os.sep):
            return None
        if os.path.isfile(full):
            return full
        if rel.startswith("assets/") or os.path.splitext(rel)[1]:
            return None
        return os.path.join(self.root, "index.html")  # SPA history fallback

    def read(self, full, accept_gzip):
        with open(full, "rb") as fh:
            data = fh.read()
        if not accept_gzip or not full.endswith(COMPRESSIBLE) or len(data) < 1024:
            return data, False
        mtime = os.path.getmtime(full)
        with self._lock:
            cached = self._gzip_cache.get(full)
            if cached and cached[0] == mtime:
                return cached[1], True
            packed = gzip.compress(data, 6)
            self._gzip_cache[full] = (mtime, packed)
        return packed, True


class PortalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 64


def make_server(app, router):
    static = StaticFiles(app.cfg["frontend_dir"])

    class Handler(BaseHTTPRequestHandler):
        server_version = "APIPortal"
        sys_version = ""
        timeout = 30

        def log_message(self, fmt, *args):  # replaced by our own access log
            pass

        def do_GET(self):
            self._dispatch("GET")

        def do_HEAD(self):
            self._dispatch("HEAD")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_PATCH(self):
            self._dispatch("PATCH")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def _dispatch(self, method):
            started = time.time()
            path = "/"
            status = 500
            try:
                split = urllib.parse.urlsplit(self.path)
                path = urllib.parse.unquote(split.path) or "/"
                if path == "/api" or path.startswith("/api/"):
                    status = self._api(method, path, split.query)
                else:
                    status = self._static(method, path)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                status = 499
            finally:
                if path.startswith("/api/") or status >= 400:
                    log.info("%s %s %s %d %.0fms", self.client_address[0], method, path, status,
                             (time.time() - started) * 1000)

        def _api(self, method, path, query_string):
            request = None
            try:
                handler, params, auth, raw = router.match("GET" if method == "HEAD" else method, path)
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    raise ApiError(413, "请求体过大")
                body = self.rfile.read(length) if length > 0 else b""
                query = {k: v[-1] for k, v in
                         urllib.parse.parse_qs(query_string, keep_blank_values=True).items()}
                request = Request(self, app, method, path, query, body, params)
                if method in ("POST", "PUT", "PATCH", "DELETE") and not raw:
                    self._check_csrf(request)
                request.authenticate(auth)
                result = handler(request, **params)
                if not isinstance(result, Response):
                    result = Response.json({"ok": True} if result is None else result)
                response = result
            except ApiError as exc:
                response = Response.json({"error": exc.message}, exc.status)
            except Exception:
                log.exception("unhandled error on %s %s", method, path)
                response = Response.json({"error": "服务器内部错误"}, 500)
            finally:
                if request is not None:
                    request.close()
            self._send(response, request.cookies_out if request else (), method == "HEAD")
            return response.status

        @staticmethod
        def _check_csrf(request):
            # A custom header cannot be sent cross-site without a CORS preflight we never allow.
            if request.headers.get("X-Requested-With") != "portal":
                raise ApiError(403, "非法请求来源")
            ctype = (request.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if request.body and ctype != "application/json":
                raise ApiError(415, "请求体必须是 JSON")
            origin = request.headers.get("Origin")
            if origin and origin != "null":
                if urllib.parse.urlsplit(origin).netloc.lower() != request.host().lower():
                    raise ApiError(403, "跨站请求被拒绝")

        def _static(self, method, path):
            if method not in ("GET", "HEAD"):
                self._send(Response.text("Method Not Allowed", 405), (), False)
                return 405
            index = os.path.join(static.root, "index.html")
            if not os.path.isfile(index):
                body = ("<h3>前端尚未构建</h3><p>请在 frontend/ 目录执行 <code>npm install && npm run build</code>，"
                        "或检查 config.json 中的 frontend_dir：%s</p>" % static.root)
                self._send(Response(body.encode("utf-8"), 503, "text/html; charset=utf-8"), (), False)
                return 503
            full = static.resolve(path)
            if full is None:
                self._send(Response.text("Not Found", 404), (), method == "HEAD")
                return 404
            accept_gzip = "gzip" in (self.headers.get("Accept-Encoding") or "")
            data, gzipped = static.read(full, accept_gzip)
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json",
                                                      "image/svg+xml"):
                ctype += "; charset=utf-8"
            headers = []
            rel = os.path.relpath(full, static.root).replace(os.sep, "/")
            if rel.startswith("assets/"):
                headers.append(("Cache-Control", "public, max-age=31536000, immutable"))
            else:
                headers.append(("Cache-Control", "no-cache"))
            if full.endswith(".html"):
                headers.append(("Content-Security-Policy", CSP))
            if gzipped:
                headers.append(("Content-Encoding", "gzip"))
            headers.append(("Vary", "Accept-Encoding"))
            self._send(Response(data, 200, ctype, headers), (), method == "HEAD")
            return 200

        def _send(self, response, cookies, head_only):
            self.send_response(response.status)
            for name, value in response.headers:
                self.send_header(name, value)
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            if not head_only and response.body:
                self.wfile.write(response.body)

    listen = app.cfg.get("listen") or "127.0.0.1"
    if ":" in listen:
        PortalServer.address_family = socket.AF_INET6
    return PortalServer((listen, int(app.cfg.get("port") or 18400)), Handler)
