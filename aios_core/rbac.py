"""Role-Based Access Control (RBAC) System for AIOS v10.4.0.

Full RBAC implementation with role hierarchy, resource-based permissions,
policy evaluation with conditions, user-role assignments, permission sets,
role constraints, and audit trail.

Classes:
    Permission      — resource:action permission (e.g. "listing:read")
    PermissionSet   — named group of permissions
    Role            — role with permissions, parent roles, constraints
    RoleHierarchy   — inheritance resolver (depth-bounded)
    AccessPolicy    — conditional access rule (time-based, IP-based)
    UserAssignment  — user ↔ role binding with audit trail
    RBACEngine      — central evaluation engine
    RBAC            — backward-compatible façade (create_role/has_permission/check_access)
"""

from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class ConstraintKind(StrEnum):
    """Role constraint types."""

    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    MAX_ROLES_PER_USER = "max_roles_per_user"


# ── Permission ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Permission:
    """Resource:action permission — e.g. 'listing:read', 'admin:write'.

    Attributes:
        resource    — what object this permission controls
        action      — what operation is allowed (read, write, delete, admin)
    """

    resource: str
    action: str

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"

    @classmethod
    def from_string(cls, perm_str: str) -> Permission:
        """Parse 'resource:action' into Permission."""
        parts = perm_str.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid permission format: '{perm_str}' — expected 'resource:action'"
            )
        return cls(resource=parts[0], action=parts[1])

    def matches(self, other: Permission) -> bool:
        """Check if this permission matches another (wildcards supported).

        resource='*' matches any resource; action='*' matches any action.
        """
        res_match = self.resource == "*" or self.resource == other.resource
        act_match = self.action == "*" or self.action == other.action
        return res_match and act_match


# ── PermissionSet ────────────────────────────────────────────────────────────


@dataclass
class PermissionSet:
    """Named group of permissions for easy assignment."""

    name: str
    permissions: set[Permission] = field(default_factory=set)

    def add(self, perm: Permission) -> None:
        """Add a permission to the set."""
        self.permissions.add(perm)

    def remove(self, perm: Permission) -> None:
        """Remove a permission from the set."""
        self.permissions.discard(perm)

    def contains(self, perm: Permission) -> bool:
        """Check if the set contains a matching permission (wildcards)."""
        return any(p.matches(perm) for p in self.permissions)

    def list_permissions(self) -> list[str]:
        """Return permission strings."""
        return sorted(str(p) for p in self.permissions)


# ── Role ─────────────────────────────────────────────────────────────────────


@dataclass
class Role:
    """Role with direct permissions, parent roles, and constraints."""

    name: str
    permissions: set[Permission] = field(default_factory=set)
    parent_roles: list[str] = field(default_factory=list)  # names of parent roles
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def add_permission(self, perm: Permission) -> None:
        """Add a permission to this role."""
        self.permissions.add(perm)

    def remove_permission(self, perm: Permission) -> None:
        """Remove a permission from this role."""
        self.permissions.discard(perm)

    def add_parent(self, parent_name: str) -> None:
        """Add a parent role for permission inheritance."""
        if parent_name not in self.parent_roles:
            self.parent_roles.append(parent_name)

    def remove_parent(self, parent_name: str) -> None:
        """Remove a parent role."""
        self.parent_roles = [p for p in self.parent_roles if p != parent_name]

    def direct_permissions(self) -> set[Permission]:
        """Return only direct permissions (not inherited)."""
        return self.permissions.copy()


# ── RoleHierarchy ────────────────────────────────────────────────────────────


class RoleHierarchy:
    """Resolve inherited permissions from parent roles.

    Depth-bounded to prevent circular inheritance issues.
    """

    MAX_DEPTH = 10

    def __init__(self) -> None:
        self.roles: dict[str, Role] = {}

    def register(self, role: Role) -> None:
        """Register a role in the hierarchy."""
        self.roles[role.name] = role

    def resolve_permissions(
        self, role_name: str, visited: set[str] | None = None, depth: int = 0
    ) -> set[Permission]:
        """Resolve all permissions for a role, including inherited.

        Uses DFS up to MAX_DEPTH to prevent circular inheritance.
        """
        if depth > self.MAX_DEPTH:
            logger.warning("Role hierarchy too deep for '%s' — truncating", role_name)
            return set()
        visited = visited or set()
        if role_name in visited:
            return set()  # circular → skip
        visited.add(role_name)

        role = self.roles.get(role_name)
        if role is None:
            return set()

        # Start with direct permissions
        all_perms = role.permissions.copy()

        # Add inherited permissions from each parent
        for parent_name in role.parent_roles:
            parent_perms = self.resolve_permissions(
                parent_name, visited.copy(), depth + 1
            )
            all_perms |= parent_perms

        return all_perms

    def all_ancestors(
        self, role_name: str, visited: set[str] | None = None
    ) -> list[str]:
        """Return list of all ancestor role names."""
        visited = visited or set()
        if role_name in visited:
            return []
        visited.add(role_name)

        role = self.roles.get(role_name)
        if role is None:
            return []

        ancestors: list[str] = []
        for parent_name in role.parent_roles:
            ancestors.append(parent_name)
            ancestors.extend(self.all_ancestors(parent_name, visited.copy()))
        return ancestors


# ── AccessPolicy ─────────────────────────────────────────────────────────────


@dataclass
class AccessPolicy:
    """Conditional access rule — evaluated at runtime.

    Conditions can restrict access based on:
    - time_of_day (hour range)
    - ip_range (CIDR)
    - platform attribute
    - custom attributes
    """

    name: str
    role_name: str
    permission: Permission
    conditions: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate all conditions against a request context."""
        for key, expected in self.conditions.items():
            if key == "time_of_day":
                # expected is (start_hour, end_hour) 0..24
                current_hour = context.get("hour", time.localtime().tm_hour)
                if not (expected[0] <= current_hour < expected[1]):
                    return False
            elif key == "ip_range":
                # expected is CIDR string
                client_ip = context.get("ip", "0.0.0.0")
                try:
                    network = ipaddress.ip_network(expected, strict=False)
                    addr = ipaddress.ip_address(client_ip)
                    if addr not in network:
                        return False
                except ValueError:
                    return False
            elif key == "platform":
                if context.get("platform", "") != expected:
                    return False
            else:
                # Generic attribute match
                if context.get(key) != expected:
                    return False
        return True


# ── UserAssignment ───────────────────────────────────────────────────────────


@dataclass
class UserAssignment:
    """Record of a user ↔ role binding."""

    user_id: str
    role_name: str
    assigned_by: str = "system"
    assigned_at: float = field(default_factory=time.time)
    expires_at: float | None = None  # None = permanent
    active: bool = True

    def is_expired(self) -> bool:
        """Check if the assignment has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


# ── RBAC Engine ──────────────────────────────────────────────────────────────


class RBACEngine:
    """Central RBAC evaluation engine.

    Features:
    - Role hierarchy with inherited permissions
    - Access policies with conditions
    - User-role assignments with expiry
    - Constraints: mutually exclusive roles, max roles per user
    - Audit trail for all access decisions
    """

    def __init__(self) -> None:
        self.hierarchy: RoleHierarchy = RoleHierarchy()
        self.policies: list[AccessPolicy] = []
        self.assignments: list[UserAssignment] = []
        self.permission_sets: dict[str, PermissionSet] = {}
        self.constraints: dict[ConstraintKind, Any] = {
            ConstraintKind.MUTUALLY_EXCLUSIVE: [],  # list of (role_a, role_b) tuples
            ConstraintKind.MAX_ROLES_PER_USER: 0,  # 0 = no limit
        }
        self.audit_log: list[dict[str, Any]] = []

    # ── Role Management ────────────────────────────────────────────

    def create_role(
        self,
        name: str,
        permissions: list[str | Permission] | None = None,
        description: str = "",
    ) -> Role:
        """Create a role with permissions (strings or Permission objects)."""
        if name in self.hierarchy.roles:
            raise ValueError(f"Role '{name}' already exists")
        perm_set: set[Permission] = set()
        if permissions:
            for p in permissions:
                if isinstance(p, str):
                    perm_set.add(Permission.from_string(p))
                elif isinstance(p, Permission):
                    perm_set.add(p)
        role = Role(name=name, permissions=perm_set, description=description)
        self.hierarchy.register(role)
        self._audit(
            "create_role", {"role": name, "permissions": [str(p) for p in perm_set]}
        )
        return role

    def delete_role(self, name: str) -> None:
        """Delete a role and remove all user assignments."""
        if name not in self.hierarchy.roles:
            raise KeyError(f"Role '{name}' not found")
        del self.hierarchy.roles[name]
        # Remove assignments
        self.assignments = [a for a in self.assignments if a.role_name != name]
        # Remove from parent_roles of other roles
        for role in self.hierarchy.roles.values():
            role.remove_parent(name)
        self._audit("delete_role", {"role": name})

    def add_permission_to_role(self, role_name: str, perm: str | Permission) -> None:
        """Add a permission to a role."""
        role = self._get_role(role_name)
        if isinstance(perm, str):
            perm = Permission.from_string(perm)
        role.add_permission(perm)
        self._audit("add_permission", {"role": role_name, "permission": str(perm)})

    def remove_permission_from_role(
        self, role_name: str, perm: str | Permission
    ) -> None:
        """Remove a permission from a role."""
        role = self._get_role(role_name)
        if isinstance(perm, str):
            perm = Permission.from_string(perm)
        role.remove_permission(perm)
        self._audit("remove_permission", {"role": role_name, "permission": str(perm)})

    def set_parent_role(self, child_name: str, parent_name: str) -> None:
        """Set a parent role for inheritance."""
        child = self._get_role(child_name)
        if parent_name not in self.hierarchy.roles:
            raise KeyError(f"Parent role '{parent_name}' not found")
        child.add_parent(parent_name)
        self._audit("set_parent", {"child": child_name, "parent": parent_name})

    def remove_parent_role(self, child_name: str, parent_name: str) -> None:
        """Remove a parent role."""
        child = self._get_role(child_name)
        child.remove_parent(parent_name)
        self._audit("remove_parent", {"child": child_name, "parent": parent_name})

    # ── Permission Sets ────────────────────────────────────────────

    def create_permission_set(
        self, name: str, permissions: list[str | Permission] | None = None
    ) -> PermissionSet:
        """Create a named permission set."""
        if name in self.permission_sets:
            raise ValueError(f"Permission set '{name}' already exists")
        ps = PermissionSet(name=name)
        if permissions:
            for p in permissions:
                if isinstance(p, str):
                    ps.add(Permission.from_string(p))
                elif isinstance(p, Permission):
                    ps.add(p)
        self.permission_sets[name] = ps
        self._audit(
            "create_permission_set",
            {"name": name, "permissions": ps.list_permissions()},
        )
        return ps

    def assign_permission_set(self, role_name: str, set_name: str) -> None:
        """Assign a permission set to a role."""
        role = self._get_role(role_name)
        ps = self.permission_sets.get(set_name)
        if ps is None:
            raise KeyError(f"Permission set '{set_name}' not found")
        for perm in ps.permissions:
            role.add_permission(perm)
        self._audit("assign_permission_set", {"role": role_name, "set": set_name})

    # ── User Assignment ────────────────────────────────────────────

    def assign_role(
        self,
        user_id: str,
        role_name: str,
        assigned_by: str = "system",
        expires_at: float | None = None,
    ) -> UserAssignment:
        """Assign a role to a user. Checks constraints."""
        self._get_role(role_name)

        # Check mutually exclusive constraint
        current_roles = self.get_user_roles(user_id)
        for role_a, role_b in self.constraints.get(
            ConstraintKind.MUTUALLY_EXCLUSIVE, []
        ):
            if role_name == role_a and role_b in current_roles:
                raise ValueError(
                    f"Roles '{role_a}' and '{role_b}' are mutually exclusive"
                )
            if role_name == role_b and role_a in current_roles:
                raise ValueError(
                    f"Roles '{role_a}' and '{role_b}' are mutually exclusive"
                )

        # Check max roles per user constraint
        max_roles = self.constraints.get(ConstraintKind.MAX_ROLES_PER_USER, 0)
        if max_roles > 0 and len(current_roles) >= max_roles:
            raise ValueError(f"User '{user_id}' exceeds max roles ({max_roles})")

        assignment = UserAssignment(
            user_id=user_id,
            role_name=role_name,
            assigned_by=assigned_by,
            expires_at=expires_at,
        )
        self.assignments.append(assignment)
        self._audit(
            "assign_role",
            {"user": user_id, "role": role_name, "assigned_by": assigned_by},
        )
        return assignment

    def revoke_role(self, user_id: str, role_name: str) -> None:
        """Revoke a role from a user."""
        self.assignments = [
            a
            for a in self.assignments
            if not (a.user_id == user_id and a.role_name == role_name)
        ]
        self._audit("revoke_role", {"user": user_id, "role": role_name})

    def get_user_roles(self, user_id: str) -> list[str]:
        """Return active role names for a user (expired assignments excluded)."""
        active: list[str] = []
        for a in self.assignments:
            if a.user_id == user_id and a.active and not a.is_expired():
                active.append(a.role_name)
        return active

    def get_user_permissions(self, user_id: str) -> set[Permission]:
        """Resolve all permissions for a user across all assigned roles."""
        roles = self.get_user_roles(user_id)
        all_perms: set[Permission] = set()
        for role_name in roles:
            all_perms |= self.hierarchy.resolve_permissions(role_name)
        return all_perms

    # ── Access Check ───────────────────────────────────────────────

    def check_access(
        self,
        user_id: str,
        permission: str | Permission,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a user has access to a permission, considering policies.

        Resolution:
        1. Resolve all user permissions (role + inheritance)
        2. Check if any permission matches the requested one (wildcard support)
        3. Check all applicable policies → if any policy blocks, return False
        4. Return True if matching permission found
        """
        if isinstance(permission, str):
            permission = Permission.from_string(permission)

        context = context or {}
        user_perms = self.get_user_permissions(user_id)

        # Step 1: check direct permission match
        has_match = any(p.matches(permission) for p in user_perms)

        if not has_match:
            self._audit(
                "access_denied",
                {
                    "user": user_id,
                    "permission": str(permission),
                    "reason": "no_matching_permission",
                },
            )
            return False

        # Step 2: check policies — any policy for this role must pass
        user_roles = self.get_user_roles(user_id)
        for policy in self.policies:
            if policy.role_name in user_roles and policy.permission.matches(permission):
                if not policy.evaluate(context):
                    self._audit(
                        "access_denied",
                        {
                            "user": user_id,
                            "permission": str(permission),
                            "reason": "policy_blocked",
                            "policy": policy.name,
                        },
                    )
                    return False

        self._audit("access_granted", {"user": user_id, "permission": str(permission)})
        return True

    def has_permission(self, role_name: str, permission: str) -> bool:
        """Check if a role (including inheritance) has a permission.

        Backward-compatible with simple RBAC.
        """
        resolved = self.hierarchy.resolve_permissions(role_name)
        perm = Permission.from_string(permission)
        return any(p.matches(perm) for p in resolved)

    # ── Policies ───────────────────────────────────────────────────

    def add_policy(self, policy: AccessPolicy) -> None:
        """Add an access policy."""
        self.policies.append(policy)
        self._audit("add_policy", {"policy": policy.name, "role": policy.role_name})

    def remove_policy(self, name: str) -> None:
        """Remove a policy by name."""
        self.policies = [p for p in self.policies if p.name != name]
        self._audit("remove_policy", {"policy": name})

    # ── Constraints ────────────────────────────────────────────────

    def set_mutually_exclusive(self, role_a: str, role_b: str) -> None:
        """Mark two roles as mutually exclusive — cannot both be assigned to same user."""
        pairs = self.constraints.get(ConstraintKind.MUTUALLY_EXCLUSIVE, [])
        if (role_a, role_b) not in pairs and (role_b, role_a) not in pairs:
            pairs.append((role_a, role_b))
        self.constraints[ConstraintKind.MUTUALLY_EXCLUSIVE] = pairs

    def set_max_roles_per_user(self, max_roles: int) -> None:
        """Set maximum number of roles any user can hold."""
        self.constraints[ConstraintKind.MAX_ROLES_PER_USER] = max_roles

    # ── Audit ──────────────────────────────────────────────────────

    def get_audit_log(
        self, user_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return audit events, optionally filtered by user_id."""
        events = [e for e in self.audit_log if e.get("user") == user_id] if user_id else self.audit_log
        return events[-limit:]

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "roles": len(self.hierarchy.roles),
            "permission_sets": len(self.permission_sets),
            "user_assignments": len(self.assignments),
            "policies": len(self.policies),
            "constraints": {
                "mutually_exclusive_pairs": len(
                    self.constraints.get(ConstraintKind.MUTUALLY_EXCLUSIVE, [])
                ),
                "max_roles_per_user": self.constraints.get(
                    ConstraintKind.MAX_ROLES_PER_USER, 0
                ),
            },
            "audit_events": len(self.audit_log),
        }

    # ── Internal ───────────────────────────────────────────────────

    def _get_role(self, name: str) -> Role:
        """Get role or raise KeyError."""
        if name not in self.hierarchy.roles:
            raise KeyError(f"Role '{name}' not found")
        return self.hierarchy.roles[name]

    def _audit(self, action: str, details: dict[str, Any]) -> None:
        """Append audit event."""
        self.audit_log.append(
            {
                "action": action,
                "timestamp": time.time(),
                **details,
            }
        )


# ── Backward-compatible façade ──────────────────────────────────────────────


class RBAC:
    """Backward-compatible simple RBAC façade.

    Preserves original create_role / has_permission / check_access / stats API.
    """

    def __init__(self) -> None:
        self.roles: dict[str, set[str]] = {}
        self.permissions: dict[str, set[str]] = {}
        self._engine: RBACEngine = RBACEngine()

    def create_role(self, role: str, permissions: list[str]) -> None:
        """Create a role with permissions (string format: 'resource:action')."""
        self.roles[role] = set(permissions)
        try:
            self._engine.create_role(role, permissions)
        except ValueError:
            # Role already exists in engine → just add permissions
            for p in permissions:
                self._engine.add_permission_to_role(role, p)

    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has a permission."""
        return permission in self.roles.get(role, set())

    def check_access(self, roles: list[str], permission: str) -> bool:
        """Check if any of the roles has the permission."""
        return any(self.has_permission(role, permission) for role in roles)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"roles": len(self.roles)}

    def engine(self) -> RBACEngine:
        """Access the underlying RBACEngine for advanced operations."""
        return self._engine


rbac = RBAC()
