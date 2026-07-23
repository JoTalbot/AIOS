"""Role-Based Access Control (RBAC) for AIOS"""

from typing import Dict, List, Set


class RBAC:
    """Simple RBAC implementation."""

    def __init__(self):
        self.roles: Dict[str, Set[str]] = {}
        self.permissions: Dict[str, Set[str]] = {}

    def create_role(self, role: str, permissions: List[str]) -> None:
        """Execute create role."""
        self.roles[role] = set(permissions)

    def has_permission(self, role: str, permission: str) -> bool:
        """Execute has permission."""
        return permission in self.roles.get(role, set())

    def check_access(self, roles: List[str], permission: str) -> bool:
        """Execute check access."""
        for role in roles:
            if self.has_permission(role, permission):
                return True
        return False

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"roles": len(self.roles)}


rbac = RBAC()
