"""Compose the runtime and FastAPI application; importing this module has no I/O."""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Match

from api.dependencies import require_admin
from api.middleware import HTTPPolicyMiddleware
from api.router import router
from api.static import FrontendFiles
from core.config import load_config
from core.constants import VERSION
from core.db import connect, init_db
from core.errors import ApiError
from core.security import RateLimiter
from integrations.cpa import CPAClient
from runtime.sync import SyncWorker
from services.settings import RuntimeSettings


class Runtime:
    """Long-lived resources shared by HTTP handlers, CLI commands and the worker."""

    def __init__(self, cfg):
        self.cfg = cfg
        os.makedirs(cfg["data_dir"], exist_ok=True)
        self.db_path = os.path.join(cfg["data_dir"], "portal.sqlite")
        init_db(self.db_path)
        self.limiter = RateLimiter()
        self.settings = RuntimeSettings(cfg, self.db)
        self.cpa = CPAClient(
            cfg["cpa"].get("base_url"),
            cfg["cpa"].get("management_key"),
            timeout=float(cfg["cpa"].get("timeout_seconds") or 8),
        )
        self.worker = SyncWorker(self)

    def db(self):
        return connect(self.db_path)


def create_app(cfg=None, *, runtime=None, start_worker=True):
    """Create an isolated app; lifecycle owns resources and a single sync worker.

    Pass cfg or Runtime for explicit configuration. The factory without arguments
    reads only backend/config/config.json, creating it on first use if missing.
    Use uvicorn runtime.app:create_app --factory.
    """

    @asynccontextmanager
    async def lifespan(app):
        nonlocal runtime
        if runtime is None:
            config = cfg if cfg is not None else load_config()
            runtime = await run_in_threadpool(Runtime, config)
        app.state.runtime = runtime
        app.state.frontend = GZipMiddleware(
            FrontendFiles(runtime.cfg["frontend_dir"]), minimum_size=1024
        )
        if start_worker:
            runtime.worker.start()
        try:
            yield
        finally:
            if start_worker:
                await run_in_threadpool(runtime.worker.stop)

    app = FastAPI(
        title="API Portal",
        version=VERSION,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )
    app.add_middleware(HTTPPolicyMiddleware)

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return JSONResponse({"error": exc.message}, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        errors = exc.errors()
        if any(item["type"] == "json_invalid" for item in errors):
            message = "请求体不是合法的 JSON"
        else:
            message = "请求参数格式不正确"
        return JSONResponse({"error": message}, 400)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        messages = {404: "接口不存在", 405: "不支持的请求方法", 400: "请求体不是合法的 JSON"}
        return JSONResponse(
            {"error": messages.get(exc.status_code, str(exc.detail))}, exc.status_code
        )

    app.include_router(router)

    @app.get("/api/openapi.json", dependencies=[Depends(require_admin)], include_in_schema=False)
    def openapi():
        return app.openapi()

    @app.get("/api/docs", dependencies=[Depends(require_admin)], include_in_schema=False)
    def docs():
        page = get_swagger_ui_html(openapi_url="/api/openapi.json", title="API Portal — API")
        html = page.body.decode("utf-8").replace(
            "SwaggerUIBundle({",
            'SwaggerUIBundle({requestInterceptor: (req) => {req.headers["X-Requested-With"] = "portal"; return req;},',
        )
        return HTMLResponse(html)

    # The frontend mount must not turn unknown /api URLs into the Vue index page.
    @app.api_route(
        "/api",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    def unknown_api(request: Request, path=""):
        # FastAPI normally reports 405. This catch-all can shadow partial matches;
        # consult only business routes to preserve that distinction.
        for route in router.routes:
            if route.matches(request.scope)[0] == Match.PARTIAL:
                raise ApiError(405, "不支持的请求方法")
        raise ApiError(404, "接口不存在")

    async def frontend(scope, receive, send):
        await app.state.frontend(scope, receive, send)

    app.mount("/", frontend, name="frontend")
    return app
