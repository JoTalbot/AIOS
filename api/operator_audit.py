"""Operator audit control-plane endpoints."""

from fastapi import APIRouter, Depends, Request


def build_operator_audit_router(service, authorize_operator):
    router = APIRouter(prefix="/operator", tags=["operator"])

    def guard(request: Request):
        return authorize_operator(request)

    @router.get("/audit", dependencies=[Depends(guard)])
    def audit():
        return service.audit_events()

    return router
