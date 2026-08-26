"""HTTP transport for the operator recovery service."""

from typing import Callable, Optional

from .recovery_api import RecoveryOperatorService

try:
    from fastapi import APIRouter, Depends, HTTPException, Request
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    APIRouter = None


if APIRouter is not None:
    class ResolveRequest(BaseModel):
        execution_id: str = Field(min_length=1)
        action: str = Field(min_length=1)

    class RetryRequest(BaseModel):
        execution_id: str = Field(min_length=1)


def build_recovery_router(service: RecoveryOperatorService, authorize_operator: Optional[Callable] = None):
    if APIRouter is None:
        raise RuntimeError("FastAPI is required for the recovery HTTP transport")

    router = APIRouter(prefix="/recovery", tags=["operator-recovery"])

    def guard(request: Request):
        if authorize_operator is None:
            raise HTTPException(status_code=403, detail="operator authorization is not configured")
        result = authorize_operator(request)
        if result is False:
            raise HTTPException(status_code=403, detail="operator authorization required")
        return True

    @router.get("/queue", dependencies=[Depends(guard)])
    def queue(action: Optional[str] = None):
        return service.list(action=action)

    @router.get("/quarantine", dependencies=[Depends(guard)])
    def quarantine():
        return service.list(action="quarantine")

    @router.get("/manual-review", dependencies=[Depends(guard)])
    def manual_review():
        return service.list(action="manual_review")

    @router.post("/resolve", dependencies=[Depends(guard)])
    def resolve(payload: ResolveRequest):
        if payload.action not in {"retry", "skip", "quarantine", "manual_review"}:
            raise HTTPException(status_code=422, detail="unsupported recovery action")
        changed = service.resolve(payload.execution_id, payload.action)
        if not changed:
            raise HTTPException(status_code=404, detail="recovery queue item not found")
        return {"resolved": True, "execution_id": payload.execution_id, "action": payload.action}

    @router.post("/retry", dependencies=[Depends(guard)])
    def retry(payload: RetryRequest):
        changed = service.resolve(payload.execution_id, "manual_review") or service.resolve(payload.execution_id, "quarantine")
        if not changed:
            raise HTTPException(status_code=404, detail="recovery queue item not found")
        return {"resolved": True, "execution_id": payload.execution_id, "action": "retry"}

    return router
