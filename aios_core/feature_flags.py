"""Feature Flags System for AIOS v10.4.0.

Dynamic feature toggles with rollout strategies, targeting rules,
flag variants, dependencies, lifecycle management, metrics tracking,
and audit logging.

Classes:
    FlagState         — ON / OFF / VARIANT lifecycle states
    RolloutStrategy   — PERCENTAGE / USER_LIST / SCHEDULED / TARGETING_RULES
    TargetingRule     — attribute-based condition (platform, region, tier)
    FeatureFlag       — full flag definition with rollout, targeting, variants
    FlagStore         — central store: register, evaluate, mutate, audit
    FeatureFlags      — backward-compatible façade (enable/disable/is_enabled)
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class FlagState(str, Enum):
    """Flag lifecycle state."""
    DRAFT = "draft"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class RolloutStrategy(str, Enum):
    """How a flag decides who sees it."""
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    SCHEDULED = "scheduled"
    TARGETING_RULES = "targeting_rules"


# ── Targeting Rule ───────────────────────────────────────────────────────────

@dataclass
class TargetingRule:
    """Single targeting condition — attribute match or range.

    Examples:
        TargetingRule("platform", "eq", "rozetka")
        TargetingRule("region", "in", ["dnipro", "kyiv"])
        TargetingRule("tier", "gte", 2)
    """
    attribute: str
    operator: str  # eq, neq, in, not_in, gte, lte, contains
    value: Any

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate this rule against a user context dict."""
        attr_val = context.get(self.attribute)
        if attr_val is None:
            return False
        op = self.operator
        if op == "eq":
            return attr_val == self.value
        if op == "neq":
            return attr_val != self.value
        if op == "in":
            return attr_val in self.value
        if op == "not_in":
            return attr_val not in self.value
        if op == "gte":
            return attr_val >= self.value
        if op == "lte":
            return attr_val <= self.value
        if op == "contains":
            return self.value in attr_val
        return False


# ── Feature Flag ─────────────────────────────────────────────────────────────

@dataclass
class FeatureFlag:
    """Complete flag definition with rollout strategy and variants."""
    name: str
    enabled: bool = False
    state: FlagState = FlagState.DRAFT
    rollout_strategy: Optional[RolloutStrategy] = None
    rollout_percentage: float = 0.0  # 0..100
    rollout_user_list: list[str] = field(default_factory=list)
    rollout_scheduled_at: Optional[float] = None  # epoch timestamp
    targeting_rules: list[TargetingRule] = field(default_factory=list)
    variants: dict[str, Any] = field(default_factory=dict)  # variant_name → value
    default_variant: str = "off"
    parent_flag: Optional[str] = None  # dependency: must be ON too
    description: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # ── metrics (mutable) ──
    evaluation_count: int = 0
    exposure_count: int = 0
    last_evaluated_at: Optional[float] = None

    def touch(self) -> None:
        """Record evaluation timestamp and bump counter."""
        self.evaluation_count += 1
        self.last_evaluated_at = time.time()

    def record_exposure(self) -> None:
        """Bump exposure counter (user actually saw the feature)."""
        self.exposure_count += 1


# ── Audit Event ──────────────────────────────────────────────────────────────

@dataclass
class AuditEvent:
    """Immutable record of a flag change."""
    flag_name: str
    action: str  # enable, disable, toggle, update, register, archive
    actor: str = "system"
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


# ── Flag Store ───────────────────────────────────────────────────────────────

class FlagStore:
    """Central flag store: register, evaluate, mutate, audit.

    Thread-safe via simple dict — suitable for single-process AIOS agents.
    """

    def __init__(self) -> None:
        self.flags: dict[str, FeatureFlag] = {}
        self.audit_log: list[AuditEvent] = []

    # ── Registration ───────────────────────────────────────────────

    def register(
        self,
        name: str,
        enabled: bool = False,
        state: FlagState = FlagState.DRAFT,
        rollout_strategy: Optional[RolloutStrategy] = None,
        rollout_percentage: float = 0.0,
        rollout_user_list: list[str] | None = None,
        rollout_scheduled_at: Optional[float] = None,
        targeting_rules: list[TargetingRule] | None = None,
        variants: dict[str, Any] | None = None,
        default_variant: str = "off",
        parent_flag: Optional[str] = None,
        description: str = "",
    ) -> FeatureFlag:
        """Register a new flag. Raises ValueError on duplicate name."""
        if name in self.flags:
            raise ValueError(f"Flag '{name}' already registered")
        flag = FeatureFlag(
            name=name,
            enabled=enabled,
            state=state,
            rollout_strategy=rollout_strategy,
            rollout_percentage=rollout_percentage,
            rollout_user_list=rollout_user_list or [],
            rollout_scheduled_at=rollout_scheduled_at,
            targeting_rules=targeting_rules or [],
            variants=variants or {},
            default_variant=default_variant,
            parent_flag=parent_flag,
            description=description,
        )
        self.flags[name] = flag
        self._audit(name, "register", details={"enabled": enabled, "state": state.value})
        logger.info("Registered flag '%s' (state=%s)", name, state.value)
        return flag

    # ── Mutations ──────────────────────────────────────────────────

    def enable(self, name: str, actor: str = "system") -> None:
        """Enable a flag (force ON)."""
        flag = self._get(name)
        flag.enabled = True
        flag.updated_at = time.time()
        self._audit(name, "enable", actor=actor)

    def disable(self, name: str, actor: str = "system") -> None:
        """Disable a flag (force OFF)."""
        flag = self._get(name)
        flag.enabled = False
        flag.updated_at = time.time()
        self._audit(name, "disable", actor=actor)

    def toggle(self, name: str, actor: str = "system") -> None:
        """Toggle a flag ON ↔ OFF."""
        flag = self._get(name)
        flag.enabled = not flag.enabled
        flag.updated_at = time.time()
        self._audit(name, "toggle", actor=actor, details={"new_state": flag.enabled})

    def archive(self, name: str, actor: str = "system") -> None:
        """Archive a flag (lifecycle end)."""
        flag = self._get(name)
        flag.state = FlagState.ARCHIVED
        flag.enabled = False
        flag.updated_at = time.time()
        self._audit(name, "archive", actor=actor)

    def set_state(self, name: str, state: FlagState, actor: str = "system") -> None:
        """Change lifecycle state of a flag."""
        flag = self._get(name)
        flag.state = state
        flag.updated_at = time.time()
        self._audit(name, "update", actor=actor, details={"state": state.value})

    def set_rollout(
        self,
        name: str,
        strategy: RolloutStrategy,
        percentage: float = 0.0,
        user_list: list[str] | None = None,
        scheduled_at: Optional[float] = None,
    ) -> None:
        """Configure rollout strategy for a flag."""
        flag = self._get(name)
        flag.rollout_strategy = strategy
        flag.rollout_percentage = percentage
        if user_list is not None:
            flag.rollout_user_list = user_list
        if scheduled_at is not None:
            flag.rollout_scheduled_at = scheduled_at
        flag.updated_at = time.time()
        self._audit(name, "update", details={"rollout_strategy": strategy.value})

    def add_targeting_rule(self, name: str, rule: TargetingRule) -> None:
        """Append a targeting rule to a flag."""
        flag = self._get(name)
        flag.targeting_rules.append(rule)
        flag.updated_at = time.time()
        self._audit(name, "update", details={"targeting_rule": f"{rule.attribute} {rule.operator} {rule.value}"})

    def add_variant(self, name: str, variant_name: str, value: Any) -> None:
        """Add or update a variant for A/B-style flag."""
        flag = self._get(name)
        flag.variants[variant_name] = value
        flag.updated_at = time.time()

    def set_parent(self, name: str, parent_name: str | None) -> None:
        """Set or clear flag dependency (parent must be ON)."""
        flag = self._get(name)
        flag.parent_flag = parent_name
        flag.updated_at = time.time()

    # ── Evaluation ─────────────────────────────────────────────────

    def is_enabled(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Evaluate whether a flag is ON for the given context.

        Resolution order:
        1. If flag is archived → always False
        2. If flag has parent_flag → parent must be ON first
        3. If flag.enabled is False → False
        4. If rollout_strategy is PERCENTAGE → hash-based percentage check
        5. If rollout_strategy is USER_LIST → check context["user_id"]
        6. If rollout_strategy is SCHEDULED → check time window
        7. If rollout_strategy is TARGETING_RULES → all rules must pass
        8. Default → flag.enabled
        """
        context = context or {}
        flag = self._get(name)
        flag.touch()

        # Archived → always off
        if flag.state == FlagState.ARCHIVED:
            return False

        # Parent dependency
        if flag.parent_flag:
            if not self.is_enabled(flag.parent_flag, context):
                return False

        # Hard off
        if not flag.enabled:
            return False

        # No rollout strategy → simple enabled check
        if flag.rollout_strategy is None:
            flag.record_exposure()
            return True

        # ── Strategy-specific evaluation ──

        if flag.rollout_strategy == RolloutStrategy.PERCENTAGE:
            user_id = context.get("user_id", "")
            hash_val = self._hash_percentage(user_id, name)
            result = hash_val < flag.rollout_percentage
            if result:
                flag.record_exposure()
            return result

        if flag.rollout_strategy == RolloutStrategy.USER_LIST:
            user_id = context.get("user_id", "")
            result = user_id in flag.rollout_user_list
            if result:
                flag.record_exposure()
            return result

        if flag.rollout_strategy == RolloutStrategy.SCHEDULED:
            now = time.time()
            if flag.rollout_scheduled_at is None:
                return False
            result = now >= flag.rollout_scheduled_at
            if result:
                flag.record_exposure()
            return result

        if flag.rollout_strategy == RolloutStrategy.TARGETING_RULES:
            result = all(rule.evaluate(context) for rule in flag.targeting_rules)
            if result:
                flag.record_exposure()
            return result

        # Fallback
        flag.record_exposure()
        return True

    def get_variant(self, name: str, context: dict[str, Any] | None = None) -> Any:
        """Evaluate flag and return variant value (or default_variant if off)."""
        context = context or {}
        if self.is_enabled(name, context) and self.flags[name].variants:
            # Hash-based variant selection
            flag = self._get(name)
            variant_keys = list(flag.variants.keys())
            if len(variant_keys) == 1:
                return flag.variants[variant_keys[0]]
            # Deterministic hash selection
            user_id = context.get("user_id", "")
            hash_val = self._hash_percentage(user_id, f"{name}_variant")
            idx = int(hash_val / 100.0 * len(variant_keys))
            return flag.variants[variant_keys[idx]]
        return self._get(name).default_variant

    # ── Queries ────────────────────────────────────────────────────

    def list_flags(self, state: FlagState | None = None) -> list[FeatureFlag]:
        """List all flags, optionally filtered by lifecycle state."""
        if state is None:
            return list(self.flags.values())
        return [f for f in self.flags.values() if f.state == state]

    def get_flag(self, name: str) -> FeatureFlag:
        """Return the flag object."""
        return self._get(name)

    def metrics(self, name: str) -> dict[str, Any]:
        """Return evaluation metrics for a flag."""
        flag = self._get(name)
        return {
            "name": flag.name,
            "evaluation_count": flag.evaluation_count,
            "exposure_count": flag.exposure_count,
            "exposure_rate": (
                flag.exposure_count / flag.evaluation_count
                if flag.evaluation_count > 0
                else 0.0
            ),
            "last_evaluated_at": flag.last_evaluated_at,
            "enabled": flag.enabled,
            "state": flag.state.value,
        }

    def all_metrics(self) -> dict[str, dict[str, Any]]:
        """Return metrics dict for all flags."""
        return {name: self.metrics(name) for name in self.flags}

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_state: dict[str, int] = {}
        for flag in self.flags.values():
            by_state[flag.state.value] = by_state.get(flag.state.value, 0) + 1
        return {
            "total_flags": len(self.flags),
            "by_state": by_state,
            "total_evaluations": sum(f.evaluation_count for f in self.flags.values()),
            "total_exposures": sum(f.exposure_count for f in self.flags.values()),
            "audit_events": len(self.audit_log),
        }

    def get_audit_log(self, flag_name: str | None = None, limit: int = 100) -> list[AuditEvent]:
        """Return audit events, optionally filtered by flag name."""
        if flag_name:
            events = [e for e in self.audit_log if e.flag_name == flag_name]
        else:
            events = self.audit_log
        return events[-limit:]

    # ── Internal ───────────────────────────────────────────────────

    def _get(self, name: str) -> FeatureFlag:
        """Retrieve flag or raise KeyError."""
        if name not in self.flags:
            raise KeyError(f"Flag '{name}' not found")
        return self.flags[name]

    def _audit(self, flag_name: str, action: str, actor: str = "system", details: dict[str, Any] | None = None) -> None:
        """Append audit event."""
        self.audit_log.append(AuditEvent(
            flag_name=flag_name,
            action=action,
            actor=actor,
            timestamp=time.time(),
            details=details or {},
        ))

    @staticmethod
    def _hash_percentage(user_id: str, salt: str) -> float:
        """Deterministic hash: returns 0.0–100.0 based on user_id + salt.

        Same user always gets same result for same flag → consistent experience.
        """
        raw = f"{user_id}:{salt}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        # Use first 8 hex chars → 0..2^32, then scale to 0..100
        int_val = int(digest[:8], 16)
        return (int_val / 0xFFFFFFFF) * 100.0


# ── Backward-compatible façade ──────────────────────────────────────────────

class FeatureFlags:
    """Backward-compatible simple façade over FlagStore.

    Preserves original enable/disable/is_enabled/toggle/list API
    while delegating to the full FlagStore internally.
    """

    def __init__(self) -> None:
        self.flags: dict[str, bool] = {}
        self._store: FlagStore = FlagStore()

    def enable(self, flag: str) -> None:
        """Enable a flag."""
        self.flags[flag] = True
        if flag in self._store.flags:
            self._store.enable(flag)
        else:
            self._store.register(flag, enabled=True)

    def disable(self, flag: str) -> None:
        """Disable a flag."""
        self.flags[flag] = False
        if flag in self._store.flags:
            self._store.disable(flag)
        else:
            self._store.register(flag, enabled=False)

    def is_enabled(self, flag: str) -> bool:
        """Check if flag is enabled."""
        return self.flags.get(flag, False)

    def toggle(self, flag: str) -> None:
        """Toggle a flag."""
        self.flags[flag] = not self.flags.get(flag, False)
        if flag in self._store.flags:
            self._store.toggle(flag)
        elif self.flags[flag]:
            self._store.register(flag, enabled=True)

    def list(self) -> dict:
        """List all flags."""
        return self.flags.copy()

    def store(self) -> FlagStore:
        """Access the underlying FlagStore for advanced operations."""
        return self._store


feature_flags = FeatureFlags()
