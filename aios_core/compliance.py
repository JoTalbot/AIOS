"""Compliance Framework for AIOS v10.6.0.

Enhanced compliance with rule engine, violation tracking, remediation
actions, audit trail, custom policies, and scoring.

Classes:
    ComplianceRule  — single compliance rule with check and remediation
    Violation       — recorded violation with severity and remediation
    ComplianceScore — aggregate compliance score per policy
    ComplianceFramework — enhanced framework with rules, violations, audit
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class ViolationSeverity(str, Enum):
    """Violation severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Compliance Rule ──────────────────────────────────────────────────────────


@dataclass
class ComplianceRule:
    """Single compliance rule with check function and remediation."""

    name: str
    policy: str  # which policy this belongs to
    check_fn: Callable[[dict[str, Any]], bool]  # returns True if compliant
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    remediation: str = ""
    description: str = ""


# ── Violation ────────────────────────────────────────────────────────────────


@dataclass
class Violation:
    """Recorded violation with severity and remediation."""

    rule_name: str
    policy: str
    severity: ViolationSeverity
    description: str = ""
    remediation: str = ""
    detected_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float | None = None

    def resolve(self) -> None:
        """Mark violation as resolved."""
        self.resolved = True
        self.resolved_at = time.time()


# ── Compliance Score ────────────────────────────────────────────────────────


@dataclass
class ComplianceScore:
    """Aggregate compliance score per policy."""

    policy: str
    total_rules: int = 0
    compliant_rules: int = 0
    violations: list[Violation] = field(default_factory=list)

    def score(self) -> float:
        """Return compliance score (0..100)."""
        if self.total_rules == 0:
            return 100.0
        return (self.compliant_rules / self.total_rules) * 100.0

    def is_compliant(self) -> bool:
        """Check if fully compliant."""
        return self.compliant_rules == self.total_rules


# ── Compliance Framework ────────────────────────────────────────────────────


class ComplianceFramework:
    """Enhanced compliance framework with rules, violations, remediation.

    Features:
    - Rule-based compliance checking (not just string lists)
    - Violation tracking with severity and remediation
    - Compliance scoring per policy
    - Custom policy registration
    - Audit trail for all compliance checks
    - Pre-built policies (GDPR, SOC2)
    """

    def __init__(self) -> None:
        self.policies: dict[str, list[str]] = {
            "gdpr": ["data_minimization", "consent", "right_to_be_forgotten"],
            "soc2": ["security", "availability", "confidentiality"],
        }
        self.rules: dict[str, ComplianceRule] = {}
        self.violations: list[Violation] = []
        self.scores: dict[str, ComplianceScore] = {}
        self.audit_log: list[dict[str, Any]] = []

    # ── Policy Management ───────────────────────────────────────

    def register_policy(self, name: str, requirements: list[str]) -> None:
        """Register a new compliance policy."""
        self.policies[name] = requirements

    def remove_policy(self, name: str) -> None:
        """Remove a policy."""
        del self.policies[name]

    # ── Rule Management ─────────────────────────────────────────

    def add_rule(self, rule: ComplianceRule) -> None:
        """Add a compliance rule."""
        self.rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        """Remove a rule."""
        del self.rules[name]

    # ── Compliance Checking ─────────────────────────────────────

    def check_compliance(self, policy: str, implemented: list[str]) -> dict[str, Any]:
        """Check compliance for a policy (backward-compatible string-based).

        Returns {policy, compliant, missing, score}.
        """
        required = self.policies.get(policy, [])
        missing = [p for p in required if p not in implemented]

        # Also check registered rules for this policy
        rule_violations: list[str] = []
        for rule in self.rules.values():
            if rule.policy == policy:
                # For string-based check, assume implemented if in list
                if rule.name not in implemented:
                    rule_violations.append(rule.name)

        all_missing = missing + rule_violations
        score_val = (
            ((len(required) - len(all_missing)) / len(required) * 100)
            if required
            else 100.0
        )

        # Record violations
        for missing_item in all_missing:
            rule = self.rules.get(missing_item)
            severity = rule.severity if rule else ViolationSeverity.MEDIUM
            remediation = rule.remediation if rule else "Implement requirement"
            violation = Violation(
                rule_name=missing_item,
                policy=policy,
                severity=severity,
                remediation=remediation,
            )
            self.violations.append(violation)

        self._audit(
            "check_compliance",
            {
                "policy": policy,
                "compliant": len(all_missing) == 0,
                "missing": all_missing,
            },
        )

        # Update score
        self.scores[policy] = ComplianceScore(
            policy=policy,
            total_rules=len(required),
            compliant_rules=len(required) - len(all_missing),
            violations=[v for v in self.violations if v.policy == policy],
        )

        return {
            "policy": policy,
            "compliant": len(all_missing) == 0,
            "missing": all_missing,
            "score": score_val,
        }

    def check_rules(
        self, context: dict[str, Any], policy: str | None = None
    ) -> list[Violation]:
        """Check all registered rules against context."""
        new_violations: list[Violation] = []
        for rule in self.rules.values():
            if policy and rule.policy != policy:
                continue
            if not rule.check_fn(context):
                violation = Violation(
                    rule_name=rule.name,
                    policy=rule.policy,
                    severity=rule.severity,
                    description=rule.description,
                    remediation=rule.remediation,
                )
                self.violations.append(violation)
                new_violations.append(violation)

        self._audit(
            "check_rules",
            {"policy": policy or "all", "violations_found": len(new_violations)},
        )
        return new_violations

    # ── Violation Management ────────────────────────────────────

    def resolve_violation(self, rule_name: str, policy: str) -> bool:
        """Resolve a violation."""
        for v in self.violations:
            if v.rule_name == rule_name and v.policy == policy and not v.resolved:
                v.resolve()
                self._audit("resolve_violation", {"rule": rule_name, "policy": policy})
                return True
        return False

    def get_violations(
        self, policy: str | None = None, unresolved_only: bool = False
    ) -> list[Violation]:
        """Return violations, optionally filtered."""
        result = self.violations
        if policy:
            result = [v for v in result if v.policy == policy]
        if unresolved_only:
            result = [v for v in result if not v.resolved]
        return result

    # ── Scoring ─────────────────────────────────────────────────

    def get_score(self, policy: str) -> ComplianceScore | None:
        """Return compliance score for a policy."""
        return self.scores.get(policy)

    def overall_score(self) -> float:
        """Return average compliance score across all policies."""
        if not self.scores:
            return 100.0
        return sum(s.score() for s in self.scores.values()) / len(self.scores)

    # ── Audit ───────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return audit events."""
        return self.audit_log[-limit:]

    def _audit(self, action: str, details: dict[str, Any]) -> None:
        self.audit_log.append({"action": action, "timestamp": time.time(), **details})

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        unresolved = sum(1 for v in self.violations if not v.resolved)
        return {
            "policies": list(self.policies.keys()),
            "rules": len(self.rules),
            "violations": len(self.violations),
            "unresolved_violations": unresolved,
            "overall_score": self.overall_score(),
        }
