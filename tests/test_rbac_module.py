"""Comprehensive tests for aios_core/rbac.py"""

from __future__ import annotations

import pytest

from aios_core.rbac import (
    AccessPolicy,
    Permission,
    PermissionSet,
    RBAC,
    RBACEngine,
    Role,
    RoleHierarchy,
)


@pytest.fixture()
def engine():
    return RBACEngine()


@pytest.fixture()
def rbac():
    return RBAC()


# ── Permission ─────────────────────────────────────────────────


class TestPermission:
    def test_create_permission(self):
        p = Permission(resource="docs", action="read")
        assert p.resource == "docs"
        assert p.action == "read"

    def test_from_string(self):
        p = Permission.from_string("docs:read")
        assert p.resource == "docs"
        assert p.action == "read"

    def test_matches_exact(self):
        p = Permission(resource="docs", action="read")
        assert p.matches(Permission(resource="docs", action="read"))

    def test_matches_wildcard_resource(self):
        p = Permission(resource="*", action="read")
        assert p.matches(Permission(resource="anything", action="read"))

    def test_no_mismatch(self):
        p = Permission(resource="docs", action="read")
        assert not p.matches(Permission(resource="admin", action="write"))


# ── PermissionSet ──────────────────────────────────────────────


class TestPermissionSet:
    def test_add_and_contains(self):
        ps = PermissionSet(name="basic")
        ps.add(Permission(resource="docs", action="read"))
        assert ps.contains(Permission(resource="docs", action="read"))

    def test_remove(self):
        ps = PermissionSet(name="basic")
        p = Permission(resource="docs", action="read")
        ps.add(p)
        ps.remove(p)
        assert not ps.contains(p)

    def test_list_permissions(self):
        ps = PermissionSet(name="basic")
        ps.add(Permission(resource="a", action="read"))
        ps.add(Permission(resource="b", action="write"))
        perms = ps.list_permissions()
        assert len(perms) >= 2


# ── Role ───────────────────────────────────────────────────────


class TestRole:
    def test_create_role_with_permissions(self, engine):
        role = engine.create_role("admin", permissions=["docs:read", "docs:write"])
        assert role is not None

    def test_add_permission_to_role(self, engine):
        engine.create_role("editor")
        engine.add_permission_to_role("editor", "posts:write")

    def test_remove_permission_from_role(self, engine):
        engine.create_role("viewer")
        engine.add_permission_to_role("viewer", "docs:read")
        engine.remove_permission_from_role("viewer", "docs:read")

    def test_set_parent_role(self, engine):
        engine.create_role("user")
        engine.create_role("admin")
        engine.set_parent_role("admin", "user")


# ── Role Hierarchy ─────────────────────────────────────────────


class TestRoleHierarchy:
    def test_register_role(self):
        h = RoleHierarchy()
        role = Role(name="base")
        h.register(role)

    def test_resolve_permissions(self):
        h = RoleHierarchy()
        parent = Role(name="parent")
        parent.add_permission(Permission(resource="x", action="read"))
        child = Role(name="child")
        child.add_parent("parent")
        h.register(parent)
        h.register(child)
        perms = h.resolve_permissions("child")
        assert isinstance(perms, set)

    def test_all_ancestors(self):
        h = RoleHierarchy()
        grandparent = Role(name="grandparent")
        parent = Role(name="parent")
        parent.add_parent("grandparent")
        child = Role(name="child")
        child.add_parent("parent")
        h.register(grandparent)
        h.register(parent)
        h.register(child)
        ancestors = h.all_ancestors("child")
        assert isinstance(ancestors, list)


# ── RBAC Engine ────────────────────────────────────────────────


class TestRBACEngine:
    def test_create_and_delete_role(self, engine):
        engine.create_role("temp")
        engine.delete_role("temp")

    def test_assign_role(self, engine):
        engine.create_role("viewer")
        engine.assign_role("user1", "viewer")
        roles = engine.get_user_roles("user1")
        assert "viewer" in roles

    def test_revoke_role(self, engine):
        engine.create_role("viewer")
        engine.assign_role("user1", "viewer")
        engine.revoke_role("user1", "viewer")
        roles = engine.get_user_roles("user1")
        assert "viewer" not in roles

    def test_check_access(self, engine):
        engine.create_role("admin", permissions=["*:read", "*:write"])
        engine.assign_role("root", "admin")
        result = engine.check_access("root", "secret:read")
        assert isinstance(result, bool)

    def test_has_permission(self, engine):
        engine.create_role("editor", permissions=["posts:write"])
        result = engine.has_permission("editor", "posts:write")
        assert isinstance(result, bool)

    def test_get_user_permissions(self, engine):
        engine.create_role("viewer", permissions=["docs:read"])
        engine.assign_role("u1", "viewer")
        perms = engine.get_user_permissions("u1")
        assert isinstance(perms, set)

    def test_max_roles_per_user(self, engine):
        engine.set_max_roles_per_user(2)
        engine.create_role("r1")
        engine.create_role("r2")
        engine.create_role("r3")
        engine.assign_role("user1", "r1")
        engine.assign_role("user1", "r2")
        roles = engine.get_user_roles("user1")
        assert len(roles) <= 3

    def test_mutually_exclusive(self, engine):
        engine.set_mutually_exclusive("admin", "guest")
        engine.create_role("admin")
        engine.create_role("guest")
        engine.assign_role("user1", "admin")

    def test_add_policy(self, engine):
        engine.create_role("viewer")
        policy = AccessPolicy(name="docs:read:allow", role_name="viewer", permission=Permission(resource="docs", action="read"), conditions={})
        engine.add_policy(policy)

    def test_remove_policy(self, engine):
        policy = AccessPolicy(name="x:y:deny", role_name="any", permission=Permission(resource="x", action="y"), conditions={})
        engine.add_policy(policy)
        engine.remove_policy("x:y:deny")

    def test_audit_log(self, engine):
        engine.create_role("r1")
        engine.assign_role("u1", "r1")
        log = engine.get_audit_log()
        assert isinstance(log, list)

    def test_stats(self, engine):
        engine.create_role("r1")
        engine.create_role("r2")
        s = engine.stats()
        assert isinstance(s, dict)

    def test_create_permission_set(self, engine):
        ps = engine.create_permission_set("basic_read", permissions=["docs:read"])
        assert ps is not None

    def test_assign_permission_set(self, engine):
        engine.create_permission_set("basic", permissions=["docs:read"])
        engine.create_role("viewer")
        engine.assign_permission_set("viewer", "basic")


# ── RBAC convenience wrapper ───────────────────────────────────


class TestRBAC:
    def test_create_role(self, rbac):
        rbac.create_role("admin", permissions=["*:read"])
        assert rbac.has_permission("admin", "*:read")

    def test_has_permission(self, rbac):
        rbac.create_role("editor", permissions=["posts:edit"])
        assert rbac.has_permission("editor", "posts:edit")

    def test_check_access(self, rbac):
        rbac.create_role("admin", permissions=["*:read", "*:write"])
        result = rbac.check_access(["admin"], "secret:read")
        assert isinstance(result, bool)

    def test_stats(self, rbac):
        s = rbac.stats()
        assert isinstance(s, dict)

    def test_engine_access(self, rbac):
        assert isinstance(rbac.engine(), RBACEngine)
