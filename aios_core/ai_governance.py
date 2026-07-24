"""AI Governance Framework for AIOS v10.9.0.

AI governance and oversight with policy management,
compliance audits, risk assessment, transparency
tracking, accountability logging, and regulatory
compliance mapping.

Classes:
    Policy         — governance policy with rules and severity
    AuditResult    — compliance audit outcome
    AIGovernance   — full governance engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Policy:
    """Governance policy with rules and severity."""

    name: str
    rules: dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical
    category: str = (
        "general"  # data_privacy, safety, ethics, transparency, accountability
    )
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    violations: int = 0


@dataclass
class AuditResult:
    """Compliance audit outcome."""

    compliant: bool
    violations: list[str] = field(default_factory=list)
    score: float = 1.0
    category: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AIGovernance:
    """Full AI governance engine.

    Features:
    - Policy registration and management
    - Compliance audits with violation tracking
    - Risk assessment scoring
    - Transparency and accountability logging
    - Regulatory compliance mapping
    - Policy enforcement
    """

    def __init__(self) -> None:
        self.policies: dict[str, Policy] = {}
        self.audits: list[AuditResult] = []
        self._risk_scores: dict[str, float] = {}
        self._accountability_log: list[dict[str, Any]] = []
        self._transparency_records: list[dict[str, Any]] = []

    # ── Policy Management ──────────────────────────────────────────

    def add_policy(
        self,
        name: str,
        rules: dict[str, Any] | None = None,
        severity: str = "medium",
        category: str = "general",
    ) -> Policy:
        """Register a governance policy."""
        policy = Policy(
            name=name, rules=rules or {}, severity=severity, category=category
        )
        self.policies[name] = policy
        return policy

    def get_policy(self, name: str) -> Policy | None:
        """Return policy by name."""
        return self.policies.get(name)

    def enable_policy(self, name: str) -> None:
        """Enable a policy."""
        policy = self.policies.get(name)
        if policy:
            policy.enabled = True

    def disable_policy(self, name: str) -> None:
        """Disable a policy."""
        policy = self.policies.get(name)
        if policy:
            policy.enabled = False

    # ── Audit ──────────────────────────────────────────────────────

    def audit(self, system_state: dict[str, Any]) -> AuditResult:
        """Perform a compliance audit of system_state."""
        violations = []
        score = 1.0

        for policy_name, policy in self.policies.items():
            if not policy.enabled:
                continue

            for rule_name, rule_value in policy.rules.items():
                actual = system_state.get(rule_name)
                if actual is not None and actual != rule_value:
                    # Check for keyword violations
                    if isinstance(rule_value, str) and isinstance(actual, str):
                        if rule_value.lower() not in actual.lower():
                            violations.append(f"{policy_name}:{rule_name}")
                            score -= 0.1 * (
                                1
                                if policy.severity == "low"
                                else 2
                                if policy.severity == "medium"
                                else 3
                                if policy.severity == "high"
                                else 5
                            )
                            policy.violations += 1
                    elif actual != rule_value:
                        violations.append(f"{policy_name}:{rule_name}")
                        score -= 0.1

        score = max(0.0, score)
        result = AuditResult(
            compliant=len(violations) == 0,
            violations=violations,
            score=round(score, 4),
        )
        self.audits.append(result)
        return result

    def audit_category(
        self, system_state: dict[str, Any], category: str
    ) -> AuditResult:
        """Audit against policies of a specific category."""
        category_violations = []
        score = 1.0

        for policy_name, policy in self.policies.items():
            if policy.category != category or not policy.enabled:
                continue
            for rule_name, rule_value in policy.rules.items():
                actual = system_state.get(rule_name)
                if actual is not None and str(actual) != str(rule_value):
                    category_violations.append(f"{policy_name}:{rule_name}")
                    score -= 0.2

        score = max(0.0, score)
        result = AuditResult(
            compliant=len(category_violations) == 0,
            violations=category_violations,
            score=round(score, 4),
            category=category,
        )
        self.audits.append(result)
        return result

    # ── Risk Assessment ────────────────────────────────────────────

    def assess_risk(self, action: dict[str, Any]) -> dict[str, Any]:
        """Assess risk level of an action."""
        risk_score = 0.0
        risk_factors = []

        # Check for high-risk indicators
        if "deception" in str(action).lower():
            risk_score += 0.8
            risk_factors.append("deception_risk")
        if "harm" in str(action).lower():
            risk_score += 0.9
            risk_factors.append("harm_risk")
        if "override" in str(action).lower():
            risk_score += 0.5
            risk_factors.append("override_risk")
        if "autonomous" in str(action).lower():
            risk_score += 0.3
            risk_factors.append("autonomy_risk")

        # Policy violations increase risk
        violations = self.audit(action).violations
        risk_score += len(violations) * 0.1

        level = (
            "low"
            if risk_score < 0.3
            else "medium"
            if risk_score < 0.6
            else "high"
            if risk_score < 0.8
            else "critical"
        )

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": level,
            "risk_factors": risk_factors,
            "violations": violations,
        }

    # ── Transparency ──────────────────────────────────────────────

    def record_transparency(
        self, action: dict[str, Any], explanation: str = ""
    ) -> None:
        """Record a transparency event."""
        self._transparency_records.append(
            {
                "action": action,
                "explanation": explanation,
                "timestamp": time.time(),
            }
        )

    # ── Accountability ────────────────────────────────────────────

    def log_accountability(
        self, agent_id: str, action: str, outcome: str, decision_reason: str = ""
    ) -> None:
        """Log an accountability event."""
        self._accountability_log.append(
            {
                "agent_id": agent_id,
                "action": action,
                "outcome": outcome,
                "reason": decision_reason,
                "timestamp": time.time(),
            }
        )

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        active_policies = sum(1 for p in self.policies.values() if p.enabled)
        avg_audit_score = (
            (sum(a.score for a in self.audits) / len(self.audits))
            if self.audits
            else 1.0
        )
        return {
            "policies": len(self.policies),
            "active_policies": active_policies,
            "audits": len(self.audits),
            "avg_audit_score": round(avg_audit_score, 4),
            "transparency_events": len(self._transparency_records),
            "accountability_events": len(self._accountability_log),
        }
