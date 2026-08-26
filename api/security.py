"""Canonical control-plane authentication context and RBAC."""

from dataclasses import dataclass
from enum import Enum
import hmac
import os
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, Request


class OperatorRole(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    def allows(self, minimum: "OperatorRole") -> bool:
        rank = {OperatorRole.VIEWER: 0, OperatorRole.OPERATOR: 1, OperatorRole.ADMIN: 2}
        return rank[self] >= rank[minimum]


@dataclass(frozen=True)
class SecurityContext:
    actor: str
    role: OperatorRole
    correlation_id: str


def authenticate(request: Request) -> Optional[SecurityContext]:
    token = request.headers.get("authorization", "")
    expected = os.getenv("AIOS_OPERATOR_TOKEN")
    if not expected or not token.startswith("Bearer "):
        return None
    if not hmac.compare_digest(token[7:], expected):
        return None
    try:
        role = OperatorRole(request.headers.get("x-aios-role", OperatorRole.OPERATOR.value))
    except ValueError:
        return None
    actor = request.headers.get("x-aios-actor", "operator")
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
    return SecurityContext(actor=actor, role=role, correlation_id=correlation_id)


def require_role(request: Request, minimum: OperatorRole) -> SecurityContext:
    context = authenticate(request)
    if context is None:
        raise HTTPException(status_code=403, detail="operator authorization required")
    if not context.role.allows(minimum):
        raise HTTPException(status_code=403, detail=f"role {minimum.value} required")
    request.state.operator_context = context
    return context
