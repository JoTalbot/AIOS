"""Unified authenticated operator context for the AIOS control plane."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    def allows(self, required: "Role") -> bool:
        order = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2}
        return order[self] >= order[required]


@dataclass(frozen=True)
class OperatorContext:
    actor: str
    role: Role
    correlation_id: Optional[str] = None

    def require(self, role: Role) -> None:
        if not self.role.allows(role):
            raise PermissionError(f"role {self.role.value} cannot perform action requiring {role.value}")
