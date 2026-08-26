"""HTTP transport for the operator recovery service.

The router is deliberately transport-only: authorization is injected by the
application so execution workers cannot accidentally inherit operator access.
"""

from typing import Callable, Optional

from .recovery_api import RecoveryOperatorService

try:
    from fastapi import APIRouter, Depends, HTTPException
except ImportError:  # pragma: no cover
    APIRouter = None


def build_recovery_router(service: RecoveryOperatorService, authorize_operator: Optional[Callable] = None):
    if APIRouter is None:
        raise RuntimeError("FastAPI is required for the recovery HTTP transport")

    router = APIRouter(prefix="/recovery", tags=["operator-recovery"])

    def guard():
        if authorize_operator is not None:
            result = authorize_operator()
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
    def resolve(execution_id: str, action: str):
        try:
            return service.resolve(execution_id, action)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/retry", dependencies=[Depends(guard)])
    def retry(execution_id: str):
        try:
            return service.resolve(execution_id, "retry")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
