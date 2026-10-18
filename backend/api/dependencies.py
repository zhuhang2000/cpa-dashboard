"""Request-scoped connections, session permissions and shared HTTP parsing."""

from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

from fastapi import Depends, Request, Response

from core.constants import Role
from core.errors import ApiError
from core.security import sha256_hex
from services import accounts

SESSION_COOKIE = "portal_sid"


def get_runtime(request: Request):
    return request.app.state.runtime


def get_connection(runtime=Depends(get_runtime)):
    """One connection per request, shared by dependencies and closed on all exits."""
    conn = runtime.db()
    try:
        yield conn
    finally:
        conn.close()


def client_ip(request: Request):
    if get_runtime(request).cfg.get("trust_proxy"):
        real = request.headers.get("X-Real-IP")
        if real:
            return real.strip()
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else ""


def request_host(request: Request):
    if get_runtime(request).cfg.get("trust_proxy"):
        forwarded = request.headers.get("X-Forwarded-Host")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return (request.headers.get("Host") or "").strip()


def is_https(request: Request):
    if get_runtime(request).cfg.get("trust_proxy"):
        return request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


def origin_url(request: Request):
    return ("https://" if is_https(request) else "http://") + request_host(request)


def _session_cookie(request: Request, token, max_age):
    secure_conf = get_runtime(request).cfg.get("cookie_secure", "auto")
    secure = is_https(request) if secure_conf == "auto" else bool(secure_conf)
    value = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
    return value + ("; Secure" if secure else "")


def set_session_cookie(request: Request, response: Response, token, max_age):
    response.headers.append("Set-Cookie", _session_cookie(request, token, max_age))


def clear_session_cookie(response: Response):
    response.headers.append(
        "Set-Cookie", f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
    )


def current_user(request: Request, conn=Depends(get_connection), runtime=Depends(get_runtime)):
    request.state.session_hash = None
    jar = SimpleCookie()
    try:
        jar.load(request.headers.get("Cookie", ""))
    except CookieError:
        return None
    cookie = jar.get(SESSION_COOKIE)
    if not cookie:
        return None
    user, renewal = accounts.authenticate_session(
        conn, cookie.value, runtime.cfg.get("session_days")
    )
    if user is not None:
        request.state.session_hash = sha256_hex(cookie.value)
        if renewal is not None:
            # Middleware also applies renewal to error responses and CSV/redirects.
            request.state.renewal_cookie = _session_cookie(request, cookie.value, renewal)
    return user


def require_user(user=Depends(current_user)):
    if user is None:
        raise ApiError(401, "请先登录")
    return user


def require_admin(user=Depends(require_user)):
    if user["role"] != Role.ADMIN:
        raise ApiError(403, "需要管理员权限")
    return user


async def check_csrf(request: Request):
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if request.url.path == "/api/pay/epay/notify":
        return
    if request.headers.get("X-Requested-With") != "portal":
        raise ApiError(403, "非法请求来源")
    ctype = request.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if await request.body() and ctype != "application/json":
        raise ApiError(415, "请求体必须是 JSON")
    origin = request.headers.get("Origin")
    if (
        origin
        and origin != "null"
        and urlsplit(origin).netloc.lower() != request_host(request).lower()
    ):
        raise ApiError(403, "跨站请求被拒绝")


async def json_body(request: Request) -> dict:
    """Parse after CSRF/auth checks and retain existing field coercion in services.

    FastAPI Body parameters parse before dependencies. These existing endpoints
    deliberately validate later to preserve their error order and 400 messages.
    Router aggregation supplies their OpenAPI request-body metadata.
    """
    if not await request.body():
        return {}
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "请求体不是合法的 JSON")
    if not isinstance(body, dict):
        raise ApiError(400, "请求体必须是 JSON 对象")
    return body


def query_arg(request: Request, name, default=None):
    value = request.query_params.get(name)
    return default if value in (None, "") else value


def int_arg(request: Request, name, default, low=None, high=None):
    try:
        value = int(query_arg(request, name, default))
    except (TypeError, ValueError):
        raise ApiError(400, "参数 %s 必须是整数" % name)
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(high, value)
    return value


def pagination(request: Request, default_size=20, max_size=100):
    page = int_arg(request, "page", 1, 1)
    size = int_arg(request, "page_size", default_size, 1, max_size)
    return page, size, (page - 1) * size
