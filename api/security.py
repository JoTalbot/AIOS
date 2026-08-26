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
    """Authenticate using server-side identity configuration only.

    Actor and role are intentionally not trusted from request headers. The
    optional X-Correlation-ID header is a tracing hint, not an identity claim.
    """
    authorization = request.headers.get("authorization", "")
    expected_token = os.getenv("AIOS_OPERATOR_TOKEN")
    if not expected_token or not authorization.startswith("Bearer "):
        return None
    supplied_token = authorization[7:]
    if not supplied_token or not hmac.compare_digest(supplied_token, expected_token):
        return None

    try:
        role = OperatorRole(os.getenv("AIOS_OPERATOR_ROLE", OperatorRole.OPERATOR.value))
    except ValueError:
        return None

    actor = os.getenv("AIOS_OPERATOR_ACTOR", "operator")
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
    if len(correlation_id) > 128:
        return None
    return SecurityContext(actor=actor, role=role, correlation_id=correlation_id)


def require_role(request: Request, minimum: OperatorRole) -> SecurityContext:
    context = authenticate(request)
    if context is None:
        raise HTTPException(status_code=403, detail="operator authorization required")
    if not context.role.allows(minimum):
        raise HTTPException(status_code=403, detail=f"role {minimum.value} required")
    request.state.operator_context = context
    return context
