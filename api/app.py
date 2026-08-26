"""FastAPI application factory for AIOS control-plane endpoints."""

from typing import Callable, Optional

from fastapi import FastAPI, HTTPException, Request

from runtime.recovery_api import RecoveryOperatorService
from runtime.recovery_http import build_recovery_router
from runtime.security_context import OperatorContext


def create_app(*, recovery_service: Optional[RecoveryOperatorService] = None,
               operator_validator: Optional[Callable[[Request], Optional[OperatorContext]]] = None,
               readiness_check: Optional[Callable[[], bool]] = None):
    app = FastAPI(title="AIOS API", version="vNext")
    service = recovery_service or RecoveryOperatorService()

    def authorize(request: Request):
        if operator_validator is None:
            raise HTTPException(status_code=403, detail="operator authorization is not configured")
        context = operator_validator(request)
        if not context:
            raise HTTPException(status_code=403, detail="operator authorization required")
        request.state.operator_context = context
        return context

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "system": "AIOS"}

    @app.get("/ready", tags=["system"])
    async def ready():
        if readiness_check is not None and not readiness_check():
            raise HTTPException(status_code=503, detail="AIOS dependencies are not ready")
        return {"status": "ready", "system": "AIOS"}

    app.include_router(build_recovery_router(service, authorize_operator=authorize))
    return app
