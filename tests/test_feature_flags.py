"""Behavioral tests for aios_core/feature_flags.py."""
from __future__ import annotations

import time

import pytest

from aios_core.feature_flags import (
    FlagStore,
    FlagState,
    FeatureFlag,
    FeatureFlags,
    RolloutStrategy,
    TargetingRule,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def store() -> FlagStore:
    return FlagStore()


@pytest.fixture()
def flags() -> FeatureFlags:
    return FeatureFlags()


# ── 1. Parent dependency blocks child ─────────────────────────────────


class TestParentDependency:
    def test_parent_disabled_blocks_child(self, store: FlagStore) -> None:
        store.register("parent_flag", enabled=False)
        store.register("child_flag", enabled=True, parent_flag="parent_flag")
        assert store.is_enabled("child_flag", {}) is False

    def test_parent_enabled_allows_child(self, store: FlagStore) -> None:
        store.register("parent_flag", enabled=True)
        store.register("child_flag", enabled=True, parent_flag="parent_flag")
        assert store.is_enabled("child_flag", {}) is True

    def test_parent_not_registered_raises(self, store: FlagStore) -> None:
        store.register("child_flag", enabled=True, parent_flag="nonexistent")
        with pytest.raises(KeyError):
            store.is_enabled("child_flag", {})


# ── 2. Percentage rollout bucket consistency ──────────────────────────


class TestPercentageRollout:
    def test_percentage_deterministic_same_user(self, store: FlagStore) -> None:
        store.register(
            "pct_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=50,
        )
        result1 = store.is_enabled("pct_flag", {"user_id": "user-1"})
        result2 = store.is_enabled("pct_flag", {"user_id": "user-1"})
        assert result1 == result2

    def test_percentage_different_users_may_differ(self, store: FlagStore) -> None:
        store.register(
            "pct_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=50,
        )
        result1 = store.is_enabled("pct_flag", {"user_id": "user-1"})
        result2 = store.is_enabled("pct_flag", {"user_id": "user-2"})
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_percentage_zero_always_false(self, store: FlagStore) -> None:
        store.register(
            "pct_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=0,
        )
        assert store.is_enabled("pct_flag", {"user_id": "user-1"}) is False

    def test_percentage_hundred_always_true(self, store: FlagStore) -> None:
        store.register(
            "pct_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=100,
        )
        assert store.is_enabled("pct_flag", {"user_id": "user-1"}) is True


# ── 3. SCHEDULED strategy respects time windows ──────────────────────


class TestScheduledRollout:
    def test_scheduled_future_is_disabled(self, store: FlagStore, monkeypatch: pytest.MonkeyPatch) -> None:
        fixed_time = 1_000_000.0
        monkeypatch.setattr(time, "time", lambda: fixed_time)
        store.register(
            "sched_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.SCHEDULED,
            rollout_scheduled_at=fixed_time + 1000,
        )
        assert store.is_enabled("sched_flag", {}) is False

    def test_scheduled_past_is_enabled(self, store: FlagStore, monkeypatch: pytest.MonkeyPatch) -> None:
        fixed_time = 1_000_000.0
        monkeypatch.setattr(time, "time", lambda: fixed_time)
        store.register(
            "sched_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.SCHEDULED,
            rollout_scheduled_at=fixed_time - 1000,
        )
        assert store.is_enabled("sched_flag", {}) is True

    def test_scheduled_no_timestamp_returns_false(self, store: FlagStore) -> None:
        store.register(
            "sched_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.SCHEDULED,
        )
        assert store.is_enabled("sched_flag", {}) is False


# ── 4. Targeting rule evaluates correctly ─────────────────────────────


class TestTargetingRules:
    def test_single_rule_eq_match(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("platform", "eq", "rozetka")],
        )
        assert store.is_enabled("target_flag", {"platform": "rozetka"}) is True

    def test_single_rule_eq_no_match(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("platform", "eq", "rozetka")],
        )
        assert store.is_enabled("target_flag", {"platform": "olx"}) is False

    def test_multiple_rules_and_logic(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[
                TargetingRule("platform", "eq", "rozetka"),
                TargetingRule("country", "eq", "ua"),
            ],
        )
        assert store.is_enabled("target_flag", {"platform": "rozetka", "country": "ua"}) is True
        assert store.is_enabled("target_flag", {"platform": "rozetka", "country": "pl"}) is False
        assert store.is_enabled("target_flag", {"platform": "olx", "country": "ua"}) is False

    def test_rule_neq_operator(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("platform", "neq", "olx")],
        )
        assert store.is_enabled("target_flag", {"platform": "rozetka"}) is True
        assert store.is_enabled("target_flag", {"platform": "olx"}) is False

    def test_rule_in_operator(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("region", "in", ["dnipro", "kyiv"])],
        )
        assert store.is_enabled("target_flag", {"region": "dnipro"}) is True
        assert store.is_enabled("target_flag", {"region": "lviv"}) is False

    def test_rule_gte_operator(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("tier", "gte", 2)],
        )
        assert store.is_enabled("target_flag", {"tier": 3}) is True
        assert store.is_enabled("target_flag", {"tier": 1}) is False

    def test_rule_missing_attribute_returns_false(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("platform", "eq", "rozetka")],
        )
        assert store.is_enabled("target_flag", {}) is False


# ── 6. Archive forces off ─────────────────────────────────────────────


class TestArchive:
    def test_archive_forces_off_even_if_enabled(self, store: FlagStore) -> None:
        store.register("active_flag", enabled=True)
        store.archive("active_flag")
        assert store.is_enabled("active_flag", {}) is False

    def test_archive_sets_state_to_archived(self, store: FlagStore) -> None:
        store.register("active_flag", enabled=True)
        store.archive("active_flag")
        flag = store.get_flag("active_flag")
        assert flag.state == FlagState.ARCHIVED
        assert flag.enabled is False


# ── 7. Audit log tracks state changes ─────────────────────────────────


class TestAuditLog:
    def test_audit_log_tracks_enable_and_disable(self, store: FlagStore) -> None:
        store.register("tracked_flag")
        store.enable("tracked_flag")
        store.disable("tracked_flag")
        log = store.get_audit_log("tracked_flag")
        actions = [e.action for e in log]
        assert "enable" in actions
        assert "disable" in actions

    def test_audit_log_tracks_register_and_archive(self, store: FlagStore) -> None:
        store.register("archived_flag")
        store.archive("archived_flag")
        log = store.get_audit_log("archived_flag")
        actions = [e.action for e in log]
        assert "register" in actions
        assert "archive" in actions

    def test_audit_log_returns_limited_results(self, store: FlagStore) -> None:
        for i in range(5):
            store.register(f"flag_{i}")
        log = store.get_audit_log(limit=3)
        assert len(log) == 3


# ── 8. Variant selection ──────────────────────────────────────────────


class TestVariants:
    def test_variant_selection_returns_valid_variant(self, store: FlagStore) -> None:
        store.register(
            "variant_flag",
            enabled=True,
            variants={"A": 90, "B": 10},
        )
        result1 = store.get_variant("variant_flag", {"user_id": "user-1"})
        result2 = store.get_variant("variant_flag", {"user_id": "user-1"})
        assert result1 == result2
        assert result1 in (90, 10)

    def test_variant_selection_different_users(self, store: FlagStore) -> None:
        store.register(
            "variant_flag",
            enabled=True,
            variants={"A": 90, "B": 10},
        )
        results = {
            store.get_variant("variant_flag", {"user_id": f"user-{i}"})
            for i in range(50)
        }
        assert results.issubset({90, 10})

    def test_variant_selection_off_when_disabled(self, store: FlagStore) -> None:
        store.register(
            "variant_flag",
            enabled=False,
            variants={"A": 90, "B": 10},
            default_variant="off",
        )
        assert store.get_variant("variant_flag", {}) == "off"

    def test_variant_selection_single_variant(self, store: FlagStore) -> None:
        store.register(
            "variant_flag",
            enabled=True,
            variants={"only": "value"},
        )
        assert store.get_variant("variant_flag", {}) == "value"


# ── 9. FeatureFlags facade compatibility ──────────────────────────────


class TestFeatureFlagsFacade:
    def test_facade_enable_returns_none(self, flags: FeatureFlags) -> None:
        result = flags.enable("facade_flag")
        assert result is None

    def test_facade_is_enabled_after_enable(self, flags: FeatureFlags) -> None:
        flags.enable("facade_flag")
        assert flags.is_enabled("facade_flag") is True

    def test_facade_toggle(self, flags: FeatureFlags) -> None:
        flags.enable("toggle_flag")
        assert flags.is_enabled("toggle_flag") is True
        flags.toggle("toggle_flag")
        assert flags.is_enabled("toggle_flag") is False
        flags.toggle("toggle_flag")
        assert flags.is_enabled("toggle_flag") is True

    def test_facade_list_returns_dict(self, flags: FeatureFlags) -> None:
        flags.enable("list_flag")
        result = flags.list()
        assert isinstance(result, dict)
        assert "list_flag" in result

    def test_facade_disable(self, flags: FeatureFlags) -> None:
        flags.enable("disable_flag")
        assert flags.is_enabled("disable_flag") is True
        flags.disable("disable_flag")
        assert flags.is_enabled("disable_flag") is False

    def test_facade_store_returns_flag_store(self, flags: FeatureFlags) -> None:
        assert isinstance(flags.store(), FlagStore)


# ── Additional behavioral tests ───────────────────────────────────────


class TestAdditionalBehaviors:
    def test_unregister_raises_on_duplicate(self, store: FlagStore) -> None:
        store.register("dup_flag")
        with pytest.raises(ValueError, match="already registered"):
            store.register("dup_flag")

    def test_get_flag_returns_flag_object(self, store: FlagStore) -> None:
        flag = store.register("obj_flag", description="test flag")
        assert isinstance(flag, FeatureFlag)
        assert flag.name == "obj_flag"

    def test_get_flag_raises_on_missing(self, store: FlagStore) -> None:
        with pytest.raises(KeyError):
            store.get_flag("nonexistent")

    def test_metrics_tracks_evaluation_count(self, store: FlagStore) -> None:
        store.register("metrics_flag", enabled=True)
        store.is_enabled("metrics_flag", {})
        store.is_enabled("metrics_flag", {})
        m = store.metrics("metrics_flag")
        assert m["evaluation_count"] == 2
        assert m["exposure_count"] >= 0

    def test_stats_returns_correct_structure(self, store: FlagStore) -> None:
        store.register("stat_flag")
        s = store.stats()
        assert "total_flags" in s
        assert "by_state" in s
        assert "total_evaluations" in s
        assert "total_exposures" in s
        assert "audit_events" in s
        assert s["total_flags"] == 1

    def test_list_flags_filters_by_state(self, store: FlagStore) -> None:
        store.register("draft_flag", state=FlagState.DRAFT)
        store.register("prod_flag", state=FlagState.PRODUCTION)
        draft_flags = store.list_flags(state=FlagState.DRAFT)
        assert len(draft_flags) == 1
        assert draft_flags[0].name == "draft_flag"

    def test_user_list_rollout_strategy(self, store: FlagStore) -> None:
        store.register(
            "userlist_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.USER_LIST,
            rollout_user_list=["user-1", "user-2"],
        )
        assert store.is_enabled("userlist_flag", {"user_id": "user-1"}) is True
        assert store.is_enabled("userlist_flag", {"user_id": "user-3"}) is False

    def test_toggle_audit_log_records_toggle_action(self, store: FlagStore) -> None:
        store.register("toggle_flag")
        store.toggle("toggle_flag")
        log = store.get_audit_log("toggle_flag")
        assert any(e.action == "toggle" for e in log)

    def test_archive_audit_log_records_archive_action(self, store: FlagStore) -> None:
        store.register("arch_flag")
        store.archive("arch_flag")
        log = store.get_audit_log("arch_flag")
        assert any(e.action == "archive" for e in log)

    def test_parent_dependency_blocks_child_with_percentage(self, store: FlagStore) -> None:
        store.register("parent_pct", enabled=False)
        store.register(
            "child_pct",
            enabled=True,
            parent_flag="parent_pct",
            rollout_strategy=RolloutStrategy.PERCENTAGE,
            rollout_percentage=100,
        )
        assert store.is_enabled("child_pct", {"user_id": "user-1"}) is False

    def test_targeting_rule_with_context_none(self, store: FlagStore) -> None:
        store.register(
            "target_flag",
            enabled=True,
            rollout_strategy=RolloutStrategy.TARGETING_RULES,
            targeting_rules=[TargetingRule("platform", "eq", "rozetka")],
        )
        assert store.is_enabled("target_flag", None) is False

    def test_is_enabled_touches_evaluation_count(self, store: FlagStore) -> None:
        store.register("eval_flag", enabled=True)
        store.is_enabled("eval_flag", {})
        store.is_enabled("eval_flag", {})
        assert store.get_flag("eval_flag").evaluation_count == 2

    def test_rollout_setter_updates_strategy(self, store: FlagStore) -> None:
        store.register("rollout_flag", enabled=True)
        store.set_rollout(
            "rollout_flag",
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=75,
        )
        flag = store.get_flag("rollout_flag")
        assert flag.rollout_strategy == RolloutStrategy.PERCENTAGE
        assert flag.rollout_percentage == 75