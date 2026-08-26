"""Control-plane authentication context and role-based authorization."""

from dataclasses import dataclass
from enum import Enum
import hmac
import os
from typing import Optional

from fastapi import HTTPException, Request


class OperatorRole(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


@dataclass(frozen=True)
class SecurityContext:
    actor: str
    role: OperatorRole


def authenticate(request: Request) -> Optional[SecurityContext]:
    token = request.headers.get("authorization", "")
    expected = os.getenv("AIOS_OPERATOR_TOKEN")
    if not expected or not token.startswith("Bearer "):
        return None
    supplied = token[7:]
    if not hmac.compare_digest(supplied, expected):
        return None
    role = request.headers.get("x-aios-role", OperatorRole.OPERATOR.value)
    try:
        role_value = OperatorRole(role)
    except ValueError:
        return None
    actor = request.headers.get("x-aios-actor", "operator")
    return SecurityContext(actor=actor, role=role_value)


def require_role(request: Request, minimum: OperatorRole) -> SecurityContext:
    context = authenticate(request)
    if context is None:
        raise HTTPException(status_code=403, detail="operator authorization required")
    rank = {OperatorRole.VIEWER: 0, OperatorRole.OPERATOR: 1, OperatorRole.ADMIN: 2}
    if rank[context.role] < rank[minimum]:
        raise HTTPException(status_code=403, detail=f"role {minimum.value} required")
    return context
