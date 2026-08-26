"""FastAPI application factory for AIOS control-plane endpoints."""

from typing import Callable, Optional

from runtime.recovery_api import RecoveryOperatorService
from runtime.recovery_http import build_recovery_router

try:
    from fastapi import FastAPI, HTTPException, Request
except ImportError:  # pragma: no cover
    FastAPI = None


def create_app(*, recovery_service: Optional[RecoveryOperatorService] = None,
               operator_validator: Optional[Callable[[Request], bool]] = None):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required to create the AIOS HTTP application")

    app = FastAPI(title="AIOS API", version="vNext")
    service = recovery_service or RecoveryOperatorService()

    def authorize(request: Request):
        if operator_validator is None:
            raise HTTPException(status_code=403, detail="operator authorization is not configured")
        if not operator_validator(request):
            raise HTTPException(status_code=403, detail="operator authorization required")
        return True

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "system": "AIOS"}

    @app.get("/ready", tags=["system"])
    async def ready():
        return {"status": "ready", "system": "AIOS"}

    app.include_router(build_recovery_router(service, authorize_operator=authorize))
    return app
