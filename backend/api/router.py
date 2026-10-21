"""Collect business routers; URL and permission declarations live beside handlers."""

from fastapi import APIRouter, Depends

from api import accounts, api_keys, billing, notices, pricing, settings, usage
from api.dependencies import check_csrf, current_user, json_body

router = APIRouter(dependencies=[Depends(check_csrf), Depends(current_user)])
for module in (accounts, api_keys, billing, notices, pricing, usage, settings):
    # Existing services keep their field validation during migration. Describe
    # bodies without moving JSON parsing ahead of CSRF and authentication.
    for route in module.router.routes:
        if any(dependency.call is json_body for dependency in route.dependant.dependencies):
            route.openapi_extra = {
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}
            }
    router.include_router(module.router)
