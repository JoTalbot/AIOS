"""Tests for v10.4.0 modules: Feature Flags, RBAC, Workflow Engine.

Feature Flags:  registration, rollout strategies, targeting rules, variants,
                dependencies, lifecycle, metrics, audit, backward-compatible façade.
RBAC:           role creation/inheritance, permissions, user assignment,
                constraints, access policies, audit, backward-compatible façade.
Workflow:       DAG creation, layer computation, execution, retry, compensation,
                condition gates, templates, stats, backward-compatible façade.
"""

from __future__ import annotations

import time

import pytest

# ── Feature Flags ────────────────────────────────────────────────────────────
from aios_core.feature_flags import (
    FeatureFlags,
    FlagState,
    FlagStore,
    RolloutStrategy,
    TargetingRule,
    feature_flags,
)


class TestFeatureFlagStore:
    """Test FlagStore — full feature flag system."""

    def setup_method(self) -> None:
        self.store = FlagStore()

    # ── Registration ────────────────────────────────────────────

    def test_register_simple_flag(self) -> None:
        flag = self.store.register("dark_mode", enabled=True, description="Dark UI theme")
        assert flag.name == "dark_mode"
        assert flag.enabled is True
        assert flag.state == FlagState.DRAFT
        assert flag.description == "Dark UI theme"

    def test_register_duplicate_raises(self) -> None:
        self.store.register("test_flag")
        with pytest.raises(ValueError, match="already registered"):
            self.store.register("test_flag")

    def test_register_with_state(self) -> None:
        flag = self.store.register("prod_flag", state=FlagState.PRODUCTION, enabled=True)
        assert flag.state == FlagState.PRODUCTION

    def test_register_with_rollout_percentage(self) -> None:
        flag = self.store.register("new_ui", rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=25.0)
        assert flag.rollout_strategy == RolloutStrategy.PERCENTAGE
        assert flag.rollout_percentage == 25.0

    def test_register_with_user_list(self) -> None:
        flag = self.store.register("beta_access", rollout_strategy=RolloutStrategy.USER_LIST, rollout_user_list=["user1", "user2"])
        assert flag.rollout_strategy == RolloutStrategy.USER_LIST
        assert "user1" in flag.rollout_user_list

    def test_register_with_scheduled(self) -> None:
        ts = time.time() + 3600
        flag = self.store.register("launch_feature", rollout_strategy=RolloutStrategy.SCHEDULED, rollout_scheduled_at=ts)
        assert flag.rollout_scheduled_at == ts

    def test_register_with_parent(self) -> None:
        self.store.register("parent_flag", enabled=True)
        flag = self.store.register("child_flag", enabled=True, parent_flag="parent_flag")
        assert flag.parent_flag == "parent_flag"

    # ── Mutations ───────────────────────────────────────────────

    def test_enable_flag(self) -> None:
        self.store.register("test_flag")
        self.store.enable("test_flag")
        assert self.store.flags["test_flag"].enabled is True

    def test_disable_flag(self) -> None:
        self.store.register("test_flag", enabled=True)
        self.store.disable("test_flag")
        assert self.store.flags["test_flag"].enabled is False

    def test_toggle_flag(self) -> None:
        self.store.register("test_flag", enabled=False)
        self.store.toggle("test_flag")
        assert self.store.flags["test_flag"].enabled is True
        self.store.toggle("test_flag")
        assert self.store.flags["test_flag"].enabled is False

    def test_archive_flag(self) -> None:
        self.store.register("test_flag", enabled=True, state=FlagState.PRODUCTION)
        self.store.archive("test_flag")
        flag = self.store.flags["test_flag"]
        assert flag.state == FlagState.ARCHIVED
        assert flag.enabled is False

    def test_set_state(self) -> None:
        self.store.register("test_flag")
        self.store.set_state("test_flag", FlagState.STAGING)
        assert self.store.flags["test_flag"].state == FlagState.STAGING

    def test_set_rollout_strategy(self) -> None:
        self.store.register("test_flag", enabled=True)
        self.store.set_rollout("test_flag", RolloutStrategy.PERCENTAGE, percentage=50.0)
        flag = self.store.flags["test_flag"]
        assert flag.rollout_strategy == RolloutStrategy.PERCENTAGE
        assert flag.rollout_percentage == 50.0

    def test_add_targeting_rule(self) -> None:
        self.store.register("test_flag", enabled=True)
        rule = TargetingRule("platform", "eq", "rozetka")
        self.store.add_targeting_rule("test_flag", rule)
        assert len(self.store.flags["test_flag"].targeting_rules) == 1

    def test_add_variant(self) -> None:
        self.store.register("ab_flag", enabled=True)
        self.store.add_variant("ab_flag", "variant_a", "blue")
        self.store.add_variant("ab_flag", "variant_b", "red")
        assert self.store.flags["ab_flag"].variants["variant_a"] == "blue"

    def test_set_parent(self) -> None:
        self.store.register("parent", enabled=True)
        self.store.register("child", enabled=True)
        self.store.set_parent("child", "parent")
        assert self.store.flags["child"].parent_flag == "parent"

    def test_unknown_flag_raises_keyerror(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.store.enable("nonexistent")

    # ── Evaluation: simple ──────────────────────────────────────

    def test_is_enabled_simple_true(self) -> None:
        self.store.register("test_flag", enabled=True)
        assert self.store.is_enabled("test_flag") is True

    def test_is_enabled_simple_false(self) -> None:
        self.store.register("test_flag", enabled=False)
        assert self.store.is_enabled("test_flag") is False

    def test_archived_flag_always_false(self) -> None:
        self.store.register("test_flag", enabled=True, state=FlagState.ARCHIVED)
        assert self.store.is_enabled("test_flag") is False

    # ── Evaluation: parent dependency ───────────────────────────

    def test_parent_off_child_off(self) -> None:
        self.store.register("parent", enabled=False)
        self.store.register("child", enabled=True, parent_flag="parent")
        assert self.store.is_enabled("child") is False

    def test_parent_on_child_on(self) -> None:
        self.store.register("parent", enabled=True)
        self.store.register("child", enabled=True, parent_flag="parent")
        assert self.store.is_enabled("child") is True

    # ── Evaluation: percentage rollout ──────────────────────────

    def test_percentage_rollout_deterministic(self) -> None:
        self.store.register("pct_flag", enabled=True, rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=50.0)
        # Same user always gets same result
        ctx = {"user_id": "alice"}
        result1 = self.store.is_enabled("pct_flag", ctx)
        result2 = self.store.is_enabled("pct_flag", ctx)
        assert result1 == result2

    def test_percentage_rollout_100_percent(self) -> None:
        self.store.register("full_flag", enabled=True, rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=100.0)
        assert self.store.is_enabled("full_flag", {"user_id": "anyone"}) is True

    def test_percentage_rollout_0_percent(self) -> None:
        self.store.register("zero_flag", enabled=True, rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=0.0)
        assert self.store.is_enabled("zero_flag", {"user_id": "anyone"}) is False

    # ── Evaluation: user list ──────────────────────────────────

    def test_user_list_included(self) -> None:
        self.store.register("beta", enabled=True, rollout_strategy=RolloutStrategy.USER_LIST, rollout_user_list=["alice", "bob"])
        assert self.store.is_enabled("beta", {"user_id": "alice"}) is True

    def test_user_list_excluded(self) -> None:
        self.store.register("beta", enabled=True, rollout_strategy=RolloutStrategy.USER_LIST, rollout_user_list=["alice"])
        assert self.store.is_enabled("beta", {"user_id": "carol"}) is False

    def test_user_list_no_context(self) -> None:
        self.store.register("beta", enabled=True, rollout_strategy=RolloutStrategy.USER_LIST, rollout_user_list=["alice"])
        assert self.store.is_enabled("beta") is False  # no user_id → not in list

    # ── Evaluation: scheduled rollout ──────────────────────────

    def test_scheduled_past_time_enabled(self) -> None:
        past_time = time.time() - 100
        self.store.register("launch", enabled=True, rollout_strategy=RolloutStrategy.SCHEDULED, rollout_scheduled_at=past_time)
        assert self.store.is_enabled("launch") is True

    def test_scheduled_future_time_disabled(self) -> None:
        future_time = time.time() + 3600
        self.store.register("future_launch", enabled=True, rollout_strategy=RolloutStrategy.SCHEDULED, rollout_scheduled_at=future_time)
        assert self.store.is_enabled("future_launch") is False

    def test_scheduled_no_time_disabled(self) -> None:
        self.store.register("no_time", enabled=True, rollout_strategy=RolloutStrategy.SCHEDULED)
        assert self.store.is_enabled("no_time") is False

    # ── Evaluation: targeting rules ────────────────────────────

    def test_targeting_rule_eq_match(self) -> None:
        rule = TargetingRule("platform", "eq", "rozetka")
        assert rule.evaluate({"platform": "rozetka"}) is True

    def test_targeting_rule_eq_no_match(self) -> None:
        rule = TargetingRule("platform", "eq", "rozetka")
        assert rule.evaluate({"platform": "olx"}) is False

    def test_targeting_rule_neq(self) -> None:
        rule = TargetingRule("platform", "neq", "rozetka")
        assert rule.evaluate({"platform": "olx"}) is True
        assert rule.evaluate({"platform": "rozetka"}) is False

    def test_targeting_rule_in(self) -> None:
        rule = TargetingRule("region", "in", ["dnipro", "kyiv"])
        assert rule.evaluate({"region": "dnipro"}) is True
        assert rule.evaluate({"region": "lviv"}) is False

    def test_targeting_rule_not_in(self) -> None:
        rule = TargetingRule("region", "not_in", ["dnipro", "kyiv"])
        assert rule.evaluate({"region": "lviv"}) is True
        assert rule.evaluate({"region": "dnipro"}) is False

    def test_targeting_rule_gte(self) -> None:
        rule = TargetingRule("tier", "gte", 2)
        assert rule.evaluate({"tier": 3}) is True
        assert rule.evaluate({"tier": 1}) is False

    def test_targeting_rule_lte(self) -> None:
        rule = TargetingRule("tier", "lte", 5)
        assert rule.evaluate({"tier": 5}) is True
        assert rule.evaluate({"tier": 6}) is False

    def test_targeting_rule_contains(self) -> None:
        rule = TargetingRule("name", "contains", "pro")
        assert rule.evaluate({"name": "premium_pro"}) is True
        assert rule.evaluate({"name": "basic"}) is False

    def test_targeting_rule_missing_attribute(self) -> None:
        rule = TargetingRule("platform", "eq", "rozetka")
        assert rule.evaluate({}) is False

    def test_targeting_rules_all_match_enabled(self) -> None:
        self.store.register("targeted", enabled=True, rollout_strategy=RolloutStrategy.TARGETING_RULES)
        self.store.add_targeting_rule("targeted", TargetingRule("platform", "eq", "rozetka"))
        self.store.add_targeting_rule("targeted", TargetingRule("region", "in", ["dnipro"]))
        assert self.store.is_enabled("targeted", {"platform": "rozetka", "region": "dnipro"}) is True

    def test_targeting_rules_some_fail_disabled(self) -> None:
        self.store.register("targeted", enabled=True, rollout_strategy=RolloutStrategy.TARGETING_RULES)
        self.store.add_targeting_rule("targeted", TargetingRule("platform", "eq", "rozetka"))
        self.store.add_targeting_rule("targeted", TargetingRule("region", "in", ["dnipro"]))
        assert self.store.is_enabled("targeted", {"platform": "rozetka", "region": "lviv"}) is False

    # ── Variants ────────────────────────────────────────────────

    def test_get_variant_enabled_with_variants(self) -> None:
        self.store.register("ab_flag", enabled=True)
        self.store.add_variant("ab_flag", "a", "blue")
        self.store.add_variant("ab_flag", "b", "red")
        variant = self.store.get_variant("ab_flag", {"user_id": "test_user"})
        assert variant in ["blue", "red"]

    def test_get_variant_disabled_returns_default(self) -> None:
        self.store.register("ab_flag", enabled=False, default_variant="off")
        self.store.add_variant("ab_flag", "a", "blue")
        variant = self.store.get_variant("ab_flag")
        assert variant == "off"

    def test_get_variant_single_variant(self) -> None:
        self.store.register("single_var", enabled=True)
        self.store.add_variant("single_var", "only", "green")
        variant = self.store.get_variant("single_var", {"user_id": "alice"})
        assert variant == "green"

    # ── Metrics ─────────────────────────────────────────────────

    def test_metrics_evaluation_count(self) -> None:
        self.store.register("test_flag", enabled=True)
        self.store.is_enabled("test_flag")
        self.store.is_enabled("test_flag")
        metrics = self.store.metrics("test_flag")
        assert metrics["evaluation_count"] == 2

    def test_metrics_exposure_rate(self) -> None:
        self.store.register("test_flag", enabled=True)
        self.store.is_enabled("test_flag")
        metrics = self.store.metrics("test_flag")
        assert metrics["exposure_rate"] > 0

    def test_metrics_disabled_flag_zero_exposure(self) -> None:
        self.store.register("off_flag", enabled=False)
        self.store.is_enabled("off_flag")
        metrics = self.store.metrics("off_flag")
        assert metrics["exposure_count"] == 0

    def test_all_metrics(self) -> None:
        self.store.register("flag1", enabled=True)
        self.store.register("flag2", enabled=False)
        self.store.is_enabled("flag1")
        all_m = self.store.all_metrics()
        assert "flag1" in all_m
        assert "flag2" in all_m

    def test_stats(self) -> None:
        self.store.register("a", enabled=True, state=FlagState.PRODUCTION)
        self.store.register("b", enabled=False, state=FlagState.DRAFT)
        stats = self.store.stats()
        assert stats["total_flags"] == 2
        assert "by_state" in stats

    # ── Audit ──────────────────────────────────────────────────

    def test_audit_log_on_enable(self) -> None:
        self.store.register("test_flag")
        self.store.enable("test_flag", actor="admin")
        log = self.store.get_audit_log(flag_name="test_flag")
        assert len(log) >= 2  # register + enable
        assert log[-1].action == "enable"
        assert log[-1].actor == "admin"

    def test_audit_log_on_toggle(self) -> None:
        self.store.register("test_flag")
        self.store.toggle("test_flag")
        log = self.store.get_audit_log(flag_name="test_flag")
        toggle_events = [e for e in log if e.action == "toggle"]
        assert len(toggle_events) == 1

    def test_audit_log_limit(self) -> None:
        for i in range(20):
            self.store.register(f"flag_{i}")
        log = self.store.get_audit_log(limit=10)
        assert len(log) == 10

    def test_audit_log_all_flags(self) -> None:
        self.store.register("flag_a")
        self.store.register("flag_b")
        log = self.store.get_audit_log()
        assert len(log) >= 2

    # ── Queries ────────────────────────────────────────────────

    def test_list_flags_all(self) -> None:
        self.store.register("a")
        self.store.register("b")
        flags = self.store.list_flags()
        assert len(flags) == 2

    def test_list_flags_by_state(self) -> None:
        self.store.register("draft_flag", state=FlagState.DRAFT)
        self.store.register("prod_flag", state=FlagState.PRODUCTION)
        prod_flags = self.store.list_flags(state=FlagState.PRODUCTION)
        assert len(prod_flags) == 1
        assert prod_flags[0].name == "prod_flag"

    def test_get_flag(self) -> None:
        self.store.register("test_flag", description="test desc")
        flag = self.store.get_flag("test_flag")
        assert flag.description == "test desc"

    # ── Hash percentage ────────────────────────────────────────

    def test_hash_percentage_deterministic(self) -> None:
        val1 = FlagStore._hash_percentage("alice", "flag_x")
        val2 = FlagStore._hash_percentage("alice", "flag_x")
        assert val1 == val2

    def test_hash_percentage_different_users(self) -> None:
        val_alice = FlagStore._hash_percentage("alice", "flag_x")
        val_bob = FlagStore._hash_percentage("bob", "flag_x")
        # Extremely unlikely to be equal
        assert val_alice != val_bob

    def test_hash_percentage_range(self) -> None:
        for uid in ["user1", "user2", "user3", "user4", "user5"]:
            val = FlagStore._hash_percentage(uid, "test_flag")
            assert 0.0 <= val <= 100.0


class TestFeatureFlagsFacade:
    """Test backward-compatible FeatureFlags façade."""

    def setup_method(self) -> None:
        self.ff = FeatureFlags()

    def test_enable(self) -> None:
        self.ff.enable("dark_mode")
        assert self.ff.is_enabled("dark_mode") is True

    def test_disable(self) -> None:
        self.ff.enable("dark_mode")
        self.ff.disable("dark_mode")
        assert self.ff.is_enabled("dark_mode") is False

    def test_toggle(self) -> None:
        self.ff.enable("dark_mode")
        self.ff.toggle("dark_mode")
        assert self.ff.is_enabled("dark_mode") is False
        self.ff.toggle("dark_mode")
        assert self.ff.is_enabled("dark_mode") is True

    def test_default_disabled(self) -> None:
        assert self.ff.is_enabled("unknown_flag") is False

    def test_list(self) -> None:
        self.ff.enable("a")
        self.ff.enable("b")
        result = self.ff.list()
        assert result == {"a": True, "b": True}

    def test_store_access(self) -> None:
        store = self.ff.store()
        assert isinstance(store, FlagStore)


class TestFeatureFlagsGlobal:
    """Test global feature_flags singleton."""

    def test_global_instance(self) -> None:
        assert isinstance(feature_flags, FeatureFlags)


# ── RBAC ─────────────────────────────────────────────────────────────────────

from aios_core.rbac import (
    RBAC,
    AccessPolicy,
    Permission,
    PermissionSet,
    RBACEngine,
    Role,
    RoleHierarchy,
    UserAssignment,
    rbac,
)


class TestPermission:
    """Test Permission class."""

    def test_permission_str(self) -> None:
        p = Permission("listing", "read")
        assert str(p) == "listing:read"

    def test_from_string(self) -> None:
        p = Permission.from_string("listing:read")
        assert p.resource == "listing"
        assert p.action == "read"

    def test_from_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid permission format"):
            Permission.from_string("invalid")

    def test_matches_exact(self) -> None:
        p1 = Permission("listing", "read")
        p2 = Permission("listing", "read")
        assert p1.matches(p2) is True

    def test_matches_wildcard_resource(self) -> None:
        p1 = Permission("*", "read")
        p2 = Permission("listing", "read")
        assert p1.matches(p2) is True

    def test_matches_wildcard_action(self) -> None:
        p1 = Permission("listing", "*")
        p2 = Permission("listing", "write")
        assert p1.matches(p2) is True

    def test_matches_wildcard_both(self) -> None:
        p1 = Permission("*", "*")
        p2 = Permission("admin", "delete")
        assert p1.matches(p2) is True

    def test_no_match_different_resource(self) -> None:
        p1 = Permission("listing", "read")
        p2 = Permission("admin", "read")
        assert p1.matches(p2) is False

    def test_frozen(self) -> None:
        p = Permission("listing", "read")
        with pytest.raises(AttributeError):
            p.resource = "admin"  # frozen dataclass


class TestPermissionSet:
    """Test PermissionSet."""

    def test_add_and_contains(self) -> None:
        ps = PermissionSet("basic")
        ps.add(Permission("listing", "read"))
        assert ps.contains(Permission("listing", "read")) is True

    def test_contains_wildcard(self) -> None:
        ps = PermissionSet("admin")
        ps.add(Permission("*", "*"))
        assert ps.contains(Permission("listing", "read")) is True

    def test_remove(self) -> None:
        ps = PermissionSet("basic")
        p = Permission("listing", "read")
        ps.add(p)
        ps.remove(p)
        assert ps.contains(p) is False

    def test_list_permissions(self) -> None:
        ps = PermissionSet("basic")
        ps.add(Permission("listing", "read"))
        ps.add(Permission("listing", "write"))
        result = ps.list_permissions()
        assert result == ["listing:read", "listing:write"]


class TestRole:
    """Test Role class."""

    def test_add_permission(self) -> None:
        role = Role("viewer")
        role.add_permission(Permission("listing", "read"))
        assert len(role.permissions) == 1

    def test_remove_permission(self) -> None:
        role = Role("viewer")
        p = Permission("listing", "read")
        role.add_permission(p)
        role.remove_permission(p)
        assert len(role.permissions) == 0

    def test_add_parent(self) -> None:
        role = Role("editor")
        role.add_parent("viewer")
        assert "viewer" in role.parent_roles

    def test_remove_parent(self) -> None:
        role = Role("editor")
        role.add_parent("viewer")
        role.remove_parent("viewer")
        assert "viewer" not in role.parent_roles

    def test_direct_permissions(self) -> None:
        role = Role("viewer")
        role.add_permission(Permission("listing", "read"))
        assert role.direct_permissions() == {Permission("listing", "read")}


class TestRoleHierarchy:
    """Test RoleHierarchy — inheritance resolution."""

    def test_register_role(self) -> None:
        h = RoleHierarchy()
        role = Role("viewer", permissions={Permission("listing", "read")})
        h.register(role)
        assert "viewer" in h.roles

    def test_resolve_permissions_simple(self) -> None:
        h = RoleHierarchy()
        h.register(Role("viewer", permissions={Permission("listing", "read")}))
        resolved = h.resolve_permissions("viewer")
        assert Permission("listing", "read") in resolved

    def test_resolve_permissions_inherited(self) -> None:
        h = RoleHierarchy()
        h.register(Role("viewer", permissions={Permission("listing", "read")}))
        h.register(Role("editor", permissions={Permission("listing", "write")}, parent_roles=["viewer"]))
        resolved = h.resolve_permissions("editor")
        assert Permission("listing", "read") in resolved  # inherited
        assert Permission("listing", "write") in resolved  # direct

    def test_resolve_permissions_deep_inheritance(self) -> None:
        h = RoleHierarchy()
        h.register(Role("base", permissions={Permission("system", "read")}))
        h.register(Role("viewer", permissions={Permission("listing", "read")}, parent_roles=["base"]))
        h.register(Role("editor", permissions={Permission("listing", "write")}, parent_roles=["viewer"]))
        resolved = h.resolve_permissions("editor")
        assert Permission("system", "read") in resolved  # from base
        assert Permission("listing", "read") in resolved  # from viewer
        assert Permission("listing", "write") in resolved  # direct

    def test_resolve_permissions_circular_safe(self) -> None:
        h = RoleHierarchy()
        h.register(Role("a", permissions={Permission("x", "y")}, parent_roles=["b"]))
        h.register(Role("b", permissions={Permission("x", "z")}, parent_roles=["a"]))
        resolved_a = h.resolve_permissions("a")
        # Circular → only direct permissions returned (cycle stops)
        assert len(resolved_a) > 0  # still returns something, not infinite loop

    def test_resolve_permissions_max_depth(self) -> None:
        h = RoleHierarchy()
        # Create a chain deeper than MAX_DEPTH
        for i in range(15):
            parents = [f"role_{i-1}"] if i > 0 else []
            h.register(Role(f"role_{i}", permissions={Permission(f"r{i}", "read")}, parent_roles=parents))
        resolved = h.resolve_permissions("role_14")
        # Should not hang, should truncate at MAX_DEPTH
        assert isinstance(resolved, set)

    def test_resolve_permissions_unknown_role(self) -> None:
        h = RoleHierarchy()
        resolved = h.resolve_permissions("unknown")
        assert resolved == set()

    def test_all_ancestors(self) -> None:
        h = RoleHierarchy()
        h.register(Role("base"))
        h.register(Role("viewer", parent_roles=["base"]))
        h.register(Role("editor", parent_roles=["viewer"]))
        ancestors = h.all_ancestors("editor")
        assert "viewer" in ancestors
        assert "base" in ancestors


class TestRBACEngine:
    """Test RBACEngine — full RBAC system."""

    def setup_method(self) -> None:
        self.engine = RBACEngine()

    # ── Role Management ────────────────────────────────────────

    def test_create_role(self) -> None:
        role = self.engine.create_role("viewer", ["listing:read"])
        assert role.name == "viewer"
        assert Permission("listing", "read") in role.permissions

    def test_create_role_duplicate_raises(self) -> None:
        self.engine.create_role("viewer")
        with pytest.raises(ValueError, match="already exists"):
            self.engine.create_role("viewer")

    def test_create_role_with_permission_objects(self) -> None:
        perm = Permission("admin", "write")
        role = self.engine.create_role("admin", [perm])
        assert perm in role.permissions

    def test_delete_role(self) -> None:
        self.engine.create_role("viewer")
        self.engine.delete_role("viewer")
        assert "viewer" not in self.engine.hierarchy.roles

    def test_delete_role_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.engine.delete_role("unknown")

    def test_delete_role_removes_assignments(self) -> None:
        self.engine.create_role("viewer")
        self.engine.assign_role("alice", "viewer")
        self.engine.delete_role("viewer")
        assert self.engine.get_user_roles("alice") == []

    def test_delete_role_removes_from_parent_refs(self) -> None:
        self.engine.create_role("viewer")
        self.engine.create_role("editor")
        self.engine.set_parent_role("editor", "viewer")
        self.engine.delete_role("viewer")
        assert "viewer" not in self.engine.hierarchy.roles["editor"].parent_roles

    def test_add_permission_to_role(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.add_permission_to_role("viewer", "listing:write")
        perms = self.engine.hierarchy.resolve_permissions("viewer")
        assert Permission("listing", "write") in perms

    def test_remove_permission_from_role(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.remove_permission_from_role("viewer", "listing:read")
        perms = self.engine.hierarchy.resolve_permissions("viewer")
        assert Permission("listing", "read") not in perms

    def test_set_parent_role(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.create_role("editor", ["listing:write"])
        self.engine.set_parent_role("editor", "viewer")
        perms = self.engine.hierarchy.resolve_permissions("editor")
        assert Permission("listing", "read") in perms  # inherited

    def test_set_parent_role_unknown_parent_raises(self) -> None:
        self.engine.create_role("editor")
        with pytest.raises(KeyError, match="Parent role"):
            self.engine.set_parent_role("editor", "unknown")

    def test_remove_parent_role(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.create_role("editor", ["listing:write"])
        self.engine.set_parent_role("editor", "viewer")
        self.engine.remove_parent_role("editor", "viewer")
        perms = self.engine.hierarchy.resolve_permissions("editor")
        assert Permission("listing", "read") not in perms

    # ── Permission Sets ────────────────────────────────────────

    def test_create_permission_set(self) -> None:
        ps = self.engine.create_permission_set("basic", ["listing:read", "listing:write"])
        assert ps.name == "basic"
        assert len(ps.permissions) == 2

    def test_create_permission_set_duplicate_raises(self) -> None:
        self.engine.create_permission_set("basic")
        with pytest.raises(ValueError, match="already exists"):
            self.engine.create_permission_set("basic")

    def test_assign_permission_set(self) -> None:
        self.engine.create_role("viewer")
        self.engine.create_permission_set("basic", ["listing:read"])
        self.engine.assign_permission_set("viewer", "basic")
        perms = self.engine.hierarchy.resolve_permissions("viewer")
        assert Permission("listing", "read") in perms

    # ── User Assignment ────────────────────────────────────────

    def test_assign_role(self) -> None:
        self.engine.create_role("viewer")
        assignment = self.engine.assign_role("alice", "viewer")
        assert assignment.user_id == "alice"
        assert assignment.role_name == "viewer"
        assert assignment.active is True

    def test_assign_role_with_expiry(self) -> None:
        self.engine.create_role("viewer")
        expires = time.time() + 3600
        assignment = self.engine.assign_role("alice", "viewer", expires_at=expires)
        assert assignment.expires_at == expires

    def test_assign_role_expired_not_in_roles(self) -> None:
        self.engine.create_role("viewer")
        past = time.time() - 100  # expired
        self.engine.assign_role("alice", "viewer", expires_at=past)
        roles = self.engine.get_user_roles("alice")
        assert roles == []

    def test_assign_role_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.engine.assign_role("alice", "unknown")

    def test_revoke_role(self) -> None:
        self.engine.create_role("viewer")
        self.engine.assign_role("alice", "viewer")
        self.engine.revoke_role("alice", "viewer")
        assert self.engine.get_user_roles("alice") == []

    def test_get_user_roles(self) -> None:
        self.engine.create_role("viewer")
        self.engine.create_role("editor")
        self.engine.assign_role("alice", "viewer")
        self.engine.assign_role("alice", "editor")
        roles = self.engine.get_user_roles("alice")
        assert "viewer" in roles
        assert "editor" in roles

    def test_get_user_permissions(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        perms = self.engine.get_user_permissions("alice")
        assert Permission("listing", "read") in perms

    def test_get_user_permissions_inherited(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.create_role("editor", ["listing:write"])
        self.engine.set_parent_role("editor", "viewer")
        self.engine.assign_role("alice", "editor")
        perms = self.engine.get_user_permissions("alice")
        assert Permission("listing", "read") in perms  # inherited
        assert Permission("listing", "write") in perms  # direct

    # ── Access Check ───────────────────────────────────────────

    def test_check_access_allowed(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        assert self.engine.check_access("alice", "listing:read") is True

    def test_check_access_denied(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        assert self.engine.check_access("alice", "admin:write") is False

    def test_check_access_wildcard_permission(self) -> None:
        self.engine.create_role("admin", ["*:read"])
        self.engine.assign_role("alice", "admin")
        assert self.engine.check_access("alice", "listing:read") is True

    def test_check_access_with_permission_object(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        perm = Permission("listing", "read")
        assert self.engine.check_access("alice", perm) is True

    def test_check_access_inherited(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.create_role("editor", ["listing:write"])
        self.engine.set_parent_role("editor", "viewer")
        self.engine.assign_role("alice", "editor")
        assert self.engine.check_access("alice", "listing:read") is True

    def test_check_access_multiple_roles(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.create_role("admin", ["admin:write"])
        self.engine.assign_role("alice", "viewer")
        self.engine.assign_role("alice", "admin")
        assert self.engine.check_access("alice", "listing:read") is True
        assert self.engine.check_access("alice", "admin:write") is True

    def test_check_access_no_roles(self) -> None:
        assert self.engine.check_access("unknown_user", "listing:read") is False

    # ── Access Policies ────────────────────────────────────────

    def test_policy_time_based_blocks(self) -> None:
        self.engine.create_role("admin", ["admin:write"])
        self.engine.assign_role("alice", "admin")
        # Policy: admin:write only allowed during work hours (9-17)
        policy = AccessPolicy(
            name="work_hours_only",
            role_name="admin",
            permission=Permission("admin", "write"),
            conditions={"time_of_day": (9, 17)},
        )
        self.engine.add_policy(policy)
        # Check during work hours
        assert self.engine.check_access("alice", "admin:write", {"hour": 12}) is True
        # Check outside work hours
        assert self.engine.check_access("alice", "admin:write", {"hour": 22}) is False

    def test_policy_platform_blocks(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        policy = AccessPolicy(
            name="rozetka_only",
            role_name="viewer",
            permission=Permission("listing", "read"),
            conditions={"platform": "rozetka"},
        )
        self.engine.add_policy(policy)
        assert self.engine.check_access("alice", "listing:read", {"platform": "rozetka"}) is True
        assert self.engine.check_access("alice", "listing:read", {"platform": "olx"}) is False

    def test_remove_policy(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        policy = AccessPolicy("p1", "viewer", Permission("listing", "read"), {"platform": "rozetka"})
        self.engine.add_policy(policy)
        self.engine.remove_policy("p1")
        assert len(self.engine.policies) == 0

    # ── Constraints ────────────────────────────────────────────

    def test_mutually_exclusive_roles(self) -> None:
        self.engine.create_role("buyer")
        self.engine.create_role("seller")
        self.engine.set_mutually_exclusive("buyer", "seller")
        self.engine.assign_role("alice", "buyer")
        with pytest.raises(ValueError, match="mutually exclusive"):
            self.engine.assign_role("alice", "seller")

    def test_max_roles_per_user(self) -> None:
        self.engine.create_role("r1")
        self.engine.create_role("r2")
        self.engine.create_role("r3")
        self.engine.set_max_roles_per_user(2)
        self.engine.assign_role("alice", "r1")
        self.engine.assign_role("alice", "r2")
        with pytest.raises(ValueError, match="exceeds max roles"):
            self.engine.assign_role("alice", "r3")

    # ── Audit ──────────────────────────────────────────────────

    def test_audit_log_created(self) -> None:
        self.engine.create_role("viewer")
        assert len(self.engine.audit_log) >= 1

    def test_audit_log_assign_role(self) -> None:
        self.engine.create_role("viewer")
        self.engine.assign_role("alice", "viewer")
        events = self.engine.get_audit_log(user_id="alice")
        assert len(events) >= 1

    def test_audit_log_access_check(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        self.engine.check_access("alice", "listing:read")
        events = self.engine.get_audit_log(user_id="alice")
        assert any(e["action"] == "access_granted" for e in events)

    def test_audit_log_access_denied(self) -> None:
        self.engine.create_role("viewer", ["listing:read"])
        self.engine.assign_role("alice", "viewer")
        self.engine.check_access("alice", "admin:write")
        events = self.engine.get_audit_log(user_id="alice")
        assert any(e["action"] == "access_denied" for e in events)

    def test_audit_log_limit(self) -> None:
        for i in range(30):
            self.engine.create_role(f"role_{i}")
        events = self.engine.get_audit_log(limit=10)
        assert len(events) == 10

    # ── Stats ──────────────────────────────────────────────────

    def test_stats(self) -> None:
        self.engine.create_role("viewer")
        stats = self.engine.stats()
        assert stats["roles"] == 1
        assert stats["audit_events"] >= 1

    def test_stats_after_assignments(self) -> None:
        self.engine.create_role("viewer")
        self.engine.create_role("editor")
        self.engine.assign_role("alice", "viewer")
        stats = self.engine.stats()
        assert stats["roles"] == 2
        assert stats["user_assignments"] == 1


class TestRBACFacade:
    """Test backward-compatible RBAC façade."""

    def test_create_role(self) -> None:
        r = RBAC()
        r.create_role("viewer", ["listing:read", "listing:write"])
        assert "listing:read" in r.roles["viewer"]

    def test_has_permission(self) -> None:
        r = RBAC()
        r.create_role("viewer", ["listing:read"])
        assert r.has_permission("viewer", "listing:read") is True
        assert r.has_permission("viewer", "admin:write") is False

    def test_check_access(self) -> None:
        r = RBAC()
        r.create_role("viewer", ["listing:read"])
        r.create_role("admin", ["admin:write"])
        assert r.check_access(["viewer"], "listing:read") is True
        assert r.check_access(["viewer", "admin"], "admin:write") is True
        assert r.check_access(["viewer"], "admin:write") is False

    def test_stats(self) -> None:
        r = RBAC()
        r.create_role("viewer", ["listing:read"])
        assert r.stats() == {"roles": 1}

    def test_engine_access(self) -> None:
        r = RBAC()
        engine = r.engine()
        assert isinstance(engine, RBACEngine)


class TestRBACGlobal:
    """Test global rbac singleton."""

    def test_global_instance(self) -> None:
        assert isinstance(rbac, RBAC)


# ── Workflow Engine ──────────────────────────────────────────────────────────

from aios_core.workflow import (
    BackoffStrategy,
    CompensationAction,
    ConditionGate,
    DAGExecutor,
    RetryPolicy,
    StepStatus,
    TimeoutPolicy,
    WorkflowEngine,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTemplate,
    workflow_engine,
)


class TestRetryPolicy:
    """Test RetryPolicy."""

    def test_constant_backoff(self) -> None:
        rp = RetryPolicy(max_retries=3, backoff=BackoffStrategy.CONSTANT, initial_delay=2.0)
        assert rp.compute_delay(1) == 2.0
        assert rp.compute_delay(2) == 2.0
        assert rp.compute_delay(3) == 2.0

    def test_linear_backoff(self) -> None:
        rp = RetryPolicy(max_retries=5, backoff=BackoffStrategy.LINEAR, initial_delay=1.0)
        assert rp.compute_delay(1) == 1.0
        assert rp.compute_delay(2) == 2.0
        assert rp.compute_delay(3) == 3.0

    def test_exponential_backoff(self) -> None:
        rp = RetryPolicy(max_retries=5, backoff=BackoffStrategy.EXPONENTIAL, initial_delay=1.0)
        assert rp.compute_delay(1) == 1.0
        assert rp.compute_delay(2) == 2.0
        assert rp.compute_delay(3) == 4.0

    def test_max_delay_cap(self) -> None:
        rp = RetryPolicy(max_retries=10, backoff=BackoffStrategy.EXPONENTIAL, initial_delay=1.0, max_delay=5.0)
        assert rp.compute_delay(10) <= 5.0

    def test_should_retry_all_by_default(self) -> None:
        rp = RetryPolicy()
        assert rp.should_retry("ValueError") is True

    def test_should_retry_specific_exceptions(self) -> None:
        rp = RetryPolicy(retryable_exceptions=["ConnectionError", "TimeoutError"])
        assert rp.should_retry("ConnectionError") is True
        assert rp.should_retry("ValueError") is False


class TestTimeoutPolicy:
    """Test TimeoutPolicy."""

    def test_total_timeout(self) -> None:
        tp = TimeoutPolicy(timeout_seconds=30.0, grace_period=5.0)
        assert tp.total_timeout() == 35.0

    def test_default_timeout(self) -> None:
        tp = TimeoutPolicy()
        assert tp.timeout_seconds == 30.0


class TestCompensationAction:
    """Test CompensationAction."""

    def test_execute_success(self) -> None:
        def undo(**kwargs):
            return "rolled_back"
        comp = CompensationAction(name="undo_step", action=undo, params={"item": "test"})
        result = comp.execute()
        assert result == "rolled_back"

    def test_execute_failure_returns_none(self) -> None:
        def failing_undo(**kwargs):
            raise RuntimeError("undo failed")
        comp = CompensationAction(name="failing_undo", action=failing_undo)
        result = comp.execute()
        assert result is None


class TestConditionGate:
    """Test ConditionGate."""

    def test_condition_true(self) -> None:
        gate = ConditionGate(
            name="check_price",
            condition_fn=lambda ctx: ctx.get("price", 0) > 100,
            then_steps=["expensive_route"],
            else_steps=["cheap_route"],
        )
        assert gate.condition_fn({"price": 200}) is True
        assert gate.condition_fn({"price": 50}) is False


class TestWorkflowStep:
    """Test WorkflowStep."""

    def test_auto_id_generation(self) -> None:
        step = WorkflowStep(name="step1", action=lambda: 1)
        assert step.id != ""

    def test_duration_calculated(self) -> None:
        step = WorkflowStep(name="step1", action=lambda: 1)
        step.started_at = 100.0
        step.finished_at = 105.0
        assert step.duration() == 5.0

    def test_duration_not_started(self) -> None:
        step = WorkflowStep(name="step1")
        assert step.duration() == 0.0


class TestDAGExecutor:
    """Test DAGExecutor — layer computation."""

    def test_compute_layers_linear(self) -> None:
        executor = DAGExecutor()
        steps = {
            "s1": WorkflowStep(name="step1", action=lambda: 1, depends_on=[]),
            "s2": WorkflowStep(name="step2", action=lambda: 2, depends_on=["s1"]),
            "s3": WorkflowStep(name="step3", action=lambda: 3, depends_on=["s2"]),
        }
        layers = executor.compute_layers(steps)
        assert len(layers) == 3
        assert layers[0] == ["s1"]
        assert layers[1] == ["s2"]
        assert layers[2] == ["s3"]

    def test_compute_layers_parallel(self) -> None:
        executor = DAGExecutor()
        steps = {
            "s1": WorkflowStep(name="step1", action=lambda: 1, depends_on=[]),
            "s2": WorkflowStep(name="step2", action=lambda: 2, depends_on=[]),
            "s3": WorkflowStep(name="step3", action=lambda: 3, depends_on=["s1", "s2"]),
        }
        layers = executor.compute_layers(steps)
        assert len(layers) == 2
        assert set(layers[0]) == {"s1", "s2"}  # parallel
        assert layers[1] == ["s3"]  # after both complete

    def test_compute_layers_no_deps(self) -> None:
        executor = DAGExecutor()
        steps = {
            "s1": WorkflowStep(name="step1", action=lambda: 1, depends_on=[]),
            "s2": WorkflowStep(name="step2", action=lambda: 2, depends_on=[]),
        }
        layers = executor.compute_layers(steps)
        assert len(layers) == 1
        assert set(layers[0]) == {"s1", "s2"}

    def test_compute_layers_circular_breaks(self) -> None:
        executor = DAGExecutor()
        steps = {
            "s1": WorkflowStep(name="step1", action=lambda: 1, depends_on=["s2"]),
            "s2": WorkflowStep(name="step2", action=lambda: 2, depends_on=["s1"]),
        }
        layers = executor.compute_layers(steps)
        # Should not hang — circular detected
        assert len(layers) >= 1


class TestWorkflowEngine:
    """Test WorkflowEngine — full DAG workflow execution."""

    def setup_method(self) -> None:
        self.engine = WorkflowEngine()

    # ── Create ─────────────────────────────────────────────────

    def test_create_workflow(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        assert wf.name == "test_wf"
        assert wf.status == WorkflowStatus.PENDING
        assert wf.id in self.engine.workflows

    def test_add_step_simple(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        step = self.engine.add_step(wf.id, "step1", action=lambda: 42)
        assert step.name == "step1"
        assert len(wf.steps) == 1

    def test_add_step_with_params(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        step = self.engine.add_step(wf.id, "greet", action=lambda name="": f"Hello {name}", params={"name": "Alice"})
        assert step.params == {"name": "Alice"}

    def test_add_step_with_retry(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        retry = RetryPolicy(max_retries=3)
        step = self.engine.add_step(wf.id, "retry_step", action=lambda: 1, retry_policy=retry)
        assert step.retry_policy is not None
        assert step.retry_policy.max_retries == 3

    def test_add_step_with_depends_on(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        s1 = self.engine.add_step(wf.id, "step1", action=lambda: 1)
        s2 = self.engine.add_step(wf.id, "step2", action=lambda: 2, depends_on=[s1.id])
        assert s2.depends_on == [s1.id]

    def test_add_step_with_compensation(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        comp = CompensationAction("undo", action=lambda: "undone")
        step = self.engine.add_step(wf.id, "step1", action=lambda: 1, compensation=comp)
        assert step.compensation is not None

    # ── Execute ────────────────────────────────────────────────

    def test_execute_simple_workflow(self) -> None:
        wf = self.engine.create_workflow("simple_wf")
        self.engine.add_step(wf.id, "step1", action=lambda: 42)
        self.engine.add_step(wf.id, "step2", action=lambda: 99)
        result = self.engine.execute(wf.id)
        assert result["status"] == "completed"
        assert result["total_steps"] == 2
        assert result["steps_completed"] == 2

    def test_execute_workflow_with_result(self) -> None:
        wf = self.engine.create_workflow("result_wf")
        s1 = self.engine.add_step(wf.id, "calc", action=lambda: 42)
        result = self.engine.execute(wf.id)
        # Check step result stored
        wf_result = self.engine.get_result(wf.id)
        assert wf_result is not None
        assert wf_result.step_results[s1.id] == 42

    def test_execute_linear_chain(self) -> None:
        wf = self.engine.create_workflow("chain_wf")
        s1 = self.engine.add_step(wf.id, "first", action=lambda: 10)
        # Dependent step receives {s1.id}_result in its params
        def second_step(**kwargs):
            prev = kwargs.get(f"{s1.id}_result", 0)
            return prev + 5
        s2 = self.engine.add_step(wf.id, "second", action=second_step, depends_on=[s1.id])
        result = self.engine.execute(wf.id)
        assert result["status"] == "completed"
        wf_result = self.engine.get_result(wf.id)
        assert wf_result.step_results[s1.id] == 10
        assert wf_result.step_results[s2.id] == 15

    def test_execute_step_failure(self) -> None:
        def failing_action():
            raise RuntimeError("step failed")

        wf = self.engine.create_workflow("fail_wf")
        self.engine.add_step(wf.id, "fail_step", action=failing_action)
        result = self.engine.execute(wf.id)
        assert result["status"] == "failed"
        assert result["steps_failed"] == 1

    def test_execute_step_failure_with_compensation(self) -> None:
        undo_called = []

        def failing_action():
            raise RuntimeError("failed")

        def undo(**kwargs):
            undo_called.append(True)
            return "compensated"

        comp = CompensationAction("undo_fail", action=undo)
        wf = self.engine.create_workflow("comp_wf")
        self.engine.add_step(wf.id, "failing_step", action=failing_action, compensation=comp)
        result = self.engine.execute(wf.id)
        assert result["status"] == "failed"
        assert len(undo_called) == 1

    def test_execute_with_context(self) -> None:
        wf = self.engine.create_workflow("ctx_wf")
        self.engine.add_step(wf.id, "step1", action=lambda: 1)
        result = self.engine.execute(wf.id, context={"key": "value"})
        assert result["status"] == "completed"

    def test_execute_condition_gate_skip(self) -> None:
        wf = self.engine.create_workflow("gate_wf")
        gate = ConditionGate(
            name="price_check",
            condition_fn=lambda ctx: ctx.get("price", 0) > 100,
        )
        s1 = self.engine.add_step(wf.id, "step1", action=lambda: 1)
        s1.condition_gate = gate  # price not in context → False → skipped
        result = self.engine.execute(wf.id)
        wf_result = self.engine.get_result(wf.id)
        assert wf_result.step_statuses[s1.id] == StepStatus.SKIPPED

    def test_execute_condition_gate_pass(self) -> None:
        wf = self.engine.create_workflow("gate_pass_wf")
        gate = ConditionGate(
            name="price_check",
            condition_fn=lambda ctx: ctx.get("price", 0) > 100,
        )
        s1 = self.engine.add_step(wf.id, "step1", action=lambda: 1)
        s1.condition_gate = gate
        result = self.engine.execute(wf.id, context={"price": 200})
        wf_result = self.engine.get_result(wf.id)
        assert wf_result.step_statuses[s1.id] == StepStatus.SUCCESS

    # ── Retry ──────────────────────────────────────────────────

    def test_retry_policy_success_after_failure(self) -> None:
        # Use a mutable counter
        counter = {"n": 0}

        def eventually_succeeds():
            counter["n"] += 1
            if counter["n"] < 3:
                raise RuntimeError("not yet")
            return "success"

        wf = self.engine.create_workflow("retry_wf")
        retry = RetryPolicy(max_retries=3, backoff=BackoffStrategy.CONSTANT, initial_delay=0.01)
        self.engine.add_step(wf.id, "flaky", action=eventually_succeeds, retry_policy=retry)
        result = self.engine.execute(wf.id)
        assert result["status"] == "completed"

    def test_retry_policy_all_fail(self) -> None:
        def always_fails():
            raise RuntimeError("always fails")

        wf = self.engine.create_workflow("retry_fail_wf")
        retry = RetryPolicy(max_retries=2, backoff=BackoffStrategy.CONSTANT, initial_delay=0.01)
        self.engine.add_step(wf.id, "always_fail", action=always_fails, retry_policy=retry)
        result = self.engine.execute(wf.id)
        assert result["status"] == "failed"

    # ── Templates ──────────────────────────────────────────────

    def test_register_template(self) -> None:
        template = WorkflowTemplate(name="etl", step_definitions=[
            {"name": "extract", "params": {}},
            {"name": "transform", "params": {}, "depends_on": ["extract"]},
            {"name": "load", "params": {}, "depends_on": ["transform"]},
        ])
        self.engine.register_template(template)
        assert "etl" in self.engine.templates

    def test_create_from_template(self) -> None:
        template = WorkflowTemplate(name="etl", step_definitions=[
            {"name": "extract", "params": {}},
            {"name": "transform", "params": {}, "depends_on": ["extract"]},
            {"name": "load", "params": {}, "depends_on": ["transform"]},
        ])
        self.engine.register_template(template)
        actions = {
            "extract": lambda: "data",
            "transform": lambda: "transformed",
            "load": lambda: "loaded",
        }
        wf = self.engine.create_from_template("etl", "my_etl", actions)
        assert wf.name == "my_etl"
        assert len(wf.steps) == 3

    def test_create_from_template_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.engine.create_from_template("unknown", "test")

    # ── Query ──────────────────────────────────────────────────

    def test_list_workflows(self) -> None:
        self.engine.create_workflow("wf1")
        self.engine.create_workflow("wf2")
        workflows = self.engine.list_workflows()
        assert len(workflows) == 2

    def test_list_workflows_by_status(self) -> None:
        wf = self.engine.create_workflow("wf1")
        self.engine.add_step(wf.id, "step1", action=lambda: 1)
        self.engine.execute(wf.id)
        completed = self.engine.list_workflows(status=WorkflowStatus.COMPLETED)
        assert len(completed) >= 1

    def test_get_workflow(self) -> None:
        wf = self.engine.create_workflow("test_wf")
        found = self.engine.get_workflow(wf.id)
        assert found.name == "test_wf"

    def test_get_workflow_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.engine.get_workflow("unknown")

    def test_list_templates(self) -> None:
        self.engine.register_template(WorkflowTemplate(name="t1", step_definitions=[]))
        self.engine.register_template(WorkflowTemplate(name="t2", step_definitions=[]))
        names = self.engine.list_templates()
        assert "t1" in names
        assert "t2" in names

    # ── Stats ──────────────────────────────────────────────────

    def test_stats(self) -> None:
        self.engine.create_workflow("wf1")
        stats = self.engine.stats()
        assert stats["total_workflows"] == 1
        assert "by_status" in stats

    def test_cancel_workflow(self) -> None:
        wf = self.engine.create_workflow("wf1")
        self.engine.cancel(wf.id)
        assert wf.status == WorkflowStatus.CANCELLED

    # ── WorkflowResult ─────────────────────────────────────────

    def test_workflow_result_summary(self) -> None:
        result = WorkflowResult(
            workflow_id="test",
            status=WorkflowStatus.COMPLETED,
            step_statuses={"s1": StepStatus.SUCCESS, "s2": StepStatus.SUCCESS},
        )
        summary = result.summary()
        assert summary["status"] == "completed"
        assert summary["steps_completed"] == 2


class TestWorkflowEngineFacade:
    """Test backward-compatible WorkflowEngine façade."""

    def test_create_workflow(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("test")
        assert wf.name == "test"

    def test_add_step_returns_step(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("test")
        step = engine.add_step(wf.id, "step1", action=lambda: 1)
        assert step.name == "step1"

    def test_execute_returns_dict(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("test")
        engine.add_step(wf.id, "step1", action=lambda: 1)
        result = engine.execute(wf.id)
        assert isinstance(result, dict)
        assert result["status"] == "completed"


class TestWorkflowGlobal:
    """Test global workflow_engine singleton."""

    def test_global_instance(self) -> None:
        assert isinstance(workflow_engine, WorkflowEngine)


# ── Integration ──────────────────────────────────────────────────────────────

class TestFeatureFlagsIntegration:
    """Integration: feature flags + RBAC + workflow together."""

    def test_flag_with_rbac_access_control(self) -> None:
        """Feature flags gated by RBAC."""
        store = FlagStore()
        rbac_engine = RBACEngine()

        # Only users with admin role can toggle prod flags
        rbac_engine.create_role("flag_admin", ["flags:toggle"])
        rbac_engine.assign_role("operator_1", "flag_admin")

        store.register("new_feature", enabled=True, state=FlagState.PRODUCTION)
        # Access check before allowing toggle
        assert rbac_engine.check_access("operator_1", "flags:toggle") is True
        store.toggle("new_feature")

    def test_workflow_with_feature_flag_gate(self) -> None:
        """Workflow step gated by a feature flag condition."""
        store = FlagStore()
        store.register("advanced_etl", enabled=True)
        store.register("simple_etl", enabled=False)

        engine = WorkflowEngine()
        wf = engine.create_workflow("etl_wf")

        # Condition gate: if advanced_etl is enabled, run advanced path
        gate = ConditionGate(
            name="etl_mode",
            condition_fn=lambda ctx: ctx.get("advanced_etl", False),
        )
        s1 = engine.add_step(wf.id, "advanced_step", action=lambda: "advanced_result")
        s1.condition_gate = gate

        result = engine.execute(wf.id, context={"advanced_etl": True})
        assert result["status"] == "completed"

    def test_rbac_role_hierarchy_with_flags(self) -> None:
        """Role hierarchy + flag state management."""
        rbac_engine = RBACEngine()
        rbac_engine.create_role("viewer", ["flags:read"])
        rbac_engine.create_role("editor", ["flags:write"], description="Can edit flags")
        rbac_engine.set_parent_role("editor", "viewer")

        # Editor inherits flags:read from viewer
        assert rbac_engine.has_permission("editor", "flags:read") is True
        assert rbac_engine.has_permission("editor", "flags:write") is True


# ── Edge Cases ──────────────────────────────────────────────────────────────

class TestFeatureFlagsEdgeCases:
    """Edge case tests for Feature Flags."""

    def test_flag_with_empty_user_id_percentage(self) -> None:
        store = FlagStore()
        store.register("pct", enabled=True, rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=50.0)
        result = store.is_enabled("pct", {"user_id": ""})
        # Empty user_id still produces deterministic hash
        assert isinstance(result, bool)

    def test_flag_with_no_context_percentage(self) -> None:
        store = FlagStore()
        store.register("pct", enabled=True, rollout_strategy=RolloutStrategy.PERCENTAGE, rollout_percentage=50.0)
        # No context → empty user_id → deterministic hash
        result = store.is_enabled("pct")
        assert isinstance(result, bool)

    def test_targeting_rule_unknown_operator(self) -> None:
        rule = TargetingRule("attr", "unknown_op", "val")
        assert rule.evaluate({"attr": "val"}) is False

    def test_flag_metrics_zero_evaluations(self) -> None:
        store = FlagStore()
        store.register("never_evaluated")
        metrics = store.metrics("never_evaluated")
        assert metrics["exposure_rate"] == 0.0


class TestRBACEdgeCases:
    """Edge case tests for RBAC."""

    def test_permission_set_no_permissions(self) -> None:
        ps = PermissionSet("empty")
        assert ps.contains(Permission("x", "y")) is False

    def test_user_assignment_not_expired(self) -> None:
        ua = UserAssignment(user_id="alice", role_name="viewer")
        assert ua.is_expired() is False

    def test_user_assignment_expired(self) -> None:
        past = time.time() - 100
        ua = UserAssignment(user_id="alice", role_name="viewer", expires_at=past)
        assert ua.is_expired() is True

    def test_access_policy_ip_range(self) -> None:
        policy = AccessPolicy(
            name="ip_check",
            role_name="viewer",
            permission=Permission("listing", "read"),
            conditions={"ip_range": "192.168.0.0/16"},
        )
        assert policy.evaluate({"ip": "192.168.1.100"}) is True
        assert policy.evaluate({"ip": "10.0.0.1"}) is False

    def test_access_policy_custom_attribute(self) -> None:
        policy = AccessPolicy(
            name="custom_check",
            role_name="viewer",
            permission=Permission("listing", "read"),
            conditions={"department": "engineering"},
        )
        assert policy.evaluate({"department": "engineering"}) is True
        assert policy.evaluate({"department": "marketing"}) is False

    def test_access_policy_ip_invalid_cidr(self) -> None:
        policy = AccessPolicy(
            name="bad_ip",
            role_name="viewer",
            permission=Permission("listing", "read"),
            conditions={"ip_range": "invalid_cidr"},
        )
        assert policy.evaluate({"ip": "1.2.3.4"}) is False

    def test_check_access_multiple_users_no_overlap(self) -> None:
        engine = RBACEngine()
        engine.create_role("viewer", ["listing:read"])
        engine.assign_role("alice", "viewer")
        # Bob has no roles
        assert engine.check_access("bob", "listing:read") is False


class TestWorkflowEdgeCases:
    """Edge case tests for Workflow Engine."""

    def test_empty_workflow_execution(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("empty_wf")
        result = engine.execute(wf.id)
        assert result["status"] == "completed"
        assert result["total_steps"] == 0

    def test_step_with_no_action(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("no_action_wf")
        engine.add_step(wf.id, "noop", action=None)
        result = engine.execute(wf.id)
        assert result["status"] == "completed"

    def test_workflow_result_step_durations(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("duration_wf")
        s1 = engine.add_step(wf.id, "fast_step", action=lambda: 1)
        result = engine.execute(wf.id)
        wf_result = engine.get_result(wf.id)
        assert wf_result.step_durations[s1.id] > 0  # some duration recorded

    def test_workflow_context_passed_to_steps(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("ctx_wf")
        engine.add_step(wf.id, "step1", action=lambda: 1)
        result = engine.execute(wf.id, context={"data": "hello"})
        assert result["status"] == "completed"

    def test_step_result_passed_to_dependent(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("chain_wf")
        s1 = engine.add_step(wf.id, "producer", action=lambda: 42)
        # The dependent step should receive s1.id_result in its params
        s2 = engine.add_step(wf.id, "consumer", action=lambda **kwargs: kwargs.get(f"{s1.id}_result", 0) + 1, depends_on=[s1.id])
        result = engine.execute(wf.id)
        assert result["status"] == "completed"
        wf_result = engine.get_result(wf.id)
        # Consumer should have received 42 + 1 = 43
        assert wf_result.step_results[s2.id] == 43

    def test_retry_with_retryable_exception_only(self) -> None:
        counter = {"n": 0}

        def raises_value_error():
            counter["n"] += 1
            if counter["n"] < 2:
                raise ValueError("bad value")
            return "ok"

        engine = WorkflowEngine()
        wf = engine.create_workflow("specific_retry_wf")
        retry = RetryPolicy(max_retries=3, backoff=BackoffStrategy.CONSTANT, initial_delay=0.01, retryable_exceptions=["ValueError"])
        engine.add_step(wf.id, "specific_retry", action=raises_value_error, retry_policy=retry)
        result = engine.execute(wf.id)
        assert result["status"] == "completed"

    def test_retry_non_retryable_exception_fails(self) -> None:
        def raises_type_error():
            raise TypeError("bad type")

        engine = WorkflowEngine()
        wf = engine.create_workflow("non_retry_wf")
        retry = RetryPolicy(max_retries=3, backoff=BackoffStrategy.CONSTANT, initial_delay=0.01, retryable_exceptions=["ValueError"])
        engine.add_step(wf.id, "non_retry", action=raises_type_error, retry_policy=retry)
        result = engine.execute(wf.id)
        assert result["status"] == "failed"

    def test_compensation_reverse_order(self) -> None:
        """Compensations should run in reverse order (last added first)."""
        order = []

        def action_a():
            return "a_ok"  # succeeds first

        def undo_a(**kw):
            order.append("undo_a")
            return "comp_a"

        def action_b():
            raise RuntimeError("b fails")  # fails after a

        def undo_b(**kw):
            order.append("undo_b")
            return "comp_b"

        engine = WorkflowEngine()
        wf = engine.create_workflow("multi_comp_wf")
        comp_a = CompensationAction("undo_a", action=undo_a)
        comp_b = CompensationAction("undo_b", action=undo_b)

        # step_b depends on step_a → step_a succeeds first, then step_b fails
        s_a = engine.add_step(wf.id, "step_a", action=action_a, compensation=comp_a)
        s_b = engine.add_step(wf.id, "step_b", action=action_b, compensation=comp_b, depends_on=[s_a.id])
        result = engine.execute(wf.id)
        assert result["status"] == "failed"
        # Compensations run in reverse order: b first, then a
        assert order == ["undo_b", "undo_a"]
