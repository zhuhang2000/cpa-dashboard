"""Vue history fallback and cache policy on top of Starlette's static server."""

from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; font-src 'self' data:; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'"
)


class FrontendFiles(StaticFiles):
    def __init__(self, directory):
        super().__init__(directory=directory, check_dir=False)

    async def check_config(self):
        # An API-only deployment can run before the frontend is built.
        pass

    async def get_response(self, path, scope):
        if scope["method"] not in ("GET", "HEAD"):
            return PlainTextResponse("Method Not Allowed", 405)
        root = Path(self.directory).resolve()
        if not (root / "index.html").is_file():
            return HTMLResponse(
                "<h3>前端尚未构建</h3><p>请在 frontend/ 目录执行 <code>npm install && npm run build</code>，"
                "或检查 config.json 中的 frontend_dir：%s</p>" % root,
                503,
            )
        if "\x00" in path or not (root / path).resolve().is_relative_to(root):
            return PlainTextResponse("Not Found", 404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            if path.startswith("assets/") or Path(path).suffix:
                return PlainTextResponse("Not Found", 404)
            response = await super().get_response("index.html", scope)
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        )
        response.headers["Vary"] = "Accept-Encoding"
        if response.headers.get("Content-Type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = CSP
        return response
