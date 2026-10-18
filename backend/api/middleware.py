"""Small ASGI policy layer: body limit, HEAD compatibility and response headers."""

import logging

from starlette.responses import JSONResponse

MAX_BODY = 1 << 20
log = logging.getLogger("portal.http")


class HTTPPolicyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        api = scope["path"] == "/api" or scope["path"].startswith("/api/")
        head = scope["method"] == "HEAD"
        if head:
            scope = dict(scope, method="GET")
        state = scope.setdefault("state", {})
        started = False

        async def send_response(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers", []))
                renewal = state.get("renewal_cookie")
                if renewal:
                    # An explicit login/logout cookie takes precedence over renewal.
                    headers.insert(0, (b"set-cookie", renewal.encode("latin-1")))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    ]
                )
                if api and not any(name.lower() == b"cache-control" for name, _ in headers):
                    headers.append((b"cache-control", b"no-store"))
                message = dict(message, headers=headers)
            elif message["type"] == "http.response.body" and head:
                message = dict(message, body=b"")
            await send(message)

        try:
            if api:
                # Bound both Content-Length and chunked requests before JSON parsing.
                headers = dict(scope["headers"])
                try:
                    length = int(headers.get(b"content-length", b"0"))
                except ValueError:
                    return await JSONResponse({"error": "无效的 Content-Length"}, 400)(
                        scope, receive, send_response
                    )
                if length > MAX_BODY:
                    return await JSONResponse({"error": "请求体过大"}, 413)(
                        scope, receive, send_response
                    )
                chunks, size = [], 0
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > MAX_BODY:
                        return await JSONResponse({"error": "请求体过大"}, 413)(
                            scope, receive, send_response
                        )
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
                body = b"".join(chunks)
                delivered = False

                async def buffered_receive():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": body, "more_body": False}
                    return await receive()

                await self.app(scope, buffered_receive, send_response)
            else:
                await self.app(scope, receive, send_response)
        except Exception:
            if started:
                raise
            log.exception("unhandled error on %s %s", scope["method"], scope["path"])
            await JSONResponse({"error": "服务器内部错误"}, 500)(scope, receive, send_response)
