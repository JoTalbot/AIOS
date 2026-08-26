"""RBAC dependencies for recovery control-plane operations."""

from fastapi import HTTPException, Request

from .security_context import OperatorContext, Role


def get_operator_context(request: Request) -> OperatorContext:
    context = getattr(request.state, "operator_context", None)
    if context is None:
        raise HTTPException(status_code=401, detail="operator authentication required")
    return context


def require_role(required: Role):
    def dependency(request: Request) -> OperatorContext:
        context = get_operator_context(request)
        try:
            context.require(required)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return context
    return dependency
