"""AIOS Constitution Engine v3.0.0

Core constitutional decision-making engine that evaluates actions against
real constitutional articles and YAML policies. Replaces the v2.1.1 stub
with actual rule enforcement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .constitution_loader import ConstitutionalRule, ConstitutionLoader, ObligationLevel
from .policy_loader import PolicyLoader


class DecisionOutcome(Enum):
    """Possible outcomes of a constitutional evaluation."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


@dataclass
class EvaluationContext:
    """Context for a single action evaluation."""

    action: dict
    evaluation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    constitution_hits: list[dict] = field(default_factory=list)
    policy_hits: list[dict] = field(default_factory=list)
    violations: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """Result of a constitutional evaluation."""

    evaluation_id: str
    outcome: DecisionOutcome
    reason: str
    details: str
    constitution_version: str
    violations: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    policy_actions: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    matched_articles: list[str] = field(default_factory=list)
    matched_policies: list[str] = field(default_factory=list)


# Mapping from risk levels to policy threat levels
_RISK_TO_THREAT = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

# Actions that are constitutionally restricted and require special handling
_RESTRICTED_ACTIONS = {
    "modify_constitution": {
        "article": "ARTICLE-I",
        "reason": "Constitution modification requires human approval",
        "escalation": "human_review",
    },
    "modify_identity": {
        "article": "ARTICLE-I",
        "reason": "Identity modification is constitutionally restricted",
        "escalation": "human_review",
    },
    "remove_security": {
        "article": "ARTICLE-V",
        "reason": "Removing security controls is prohibited",
        "escalation": "immediate_isolation",
    },
    "transfer_ownership": {
        "article": "ARTICLE-I",
        "reason": "Ownership transfer requires human approval",
        "escalation": "human_review",
    },
    "destroy_records": {
        "article": "ARTICLE-II",
        "reason": "Destroying historical records is constitutionally restricted",
        "escalation": "human_review",
    },
    "direct_core_modification": {
        "article": "ARTICLE-XXXVI",
        "reason": "Direct core modification is prohibited by evolution policy",
        "escalation": "audit_and_review",
    },
    "unsafe_evolution": {
        "article": "ARTICLE-XXXVI",
        "reason": "Unsafe evolution is blocked",
        "escalation": "immediate_isolation",
    },
}


class ConstitutionEngine:
    """Evaluates actions against AIOS constitutional principles and policies.

    Loads the full constitution (67 articles) and all YAML policies at init.
    Each evaluate() call checks the action against:
    1. Required action fields (goal, scope, risk, audit_log)
    2. Constitution MUST NOT rules (prohibitions)
    3. Constitution MUST rules (requirements)
    4. YAML policy rules and threat levels
    5. Restricted action patterns
    """

    def __init__(
        self,
        constitution_dir: Optional[str] = None,
        policies_dir: Optional[str] = None,
    ) -> None:
        self.version = "3.0.0"
        self.constitution = ConstitutionLoader(constitution_dir)
        self.policies = PolicyLoader(policies_dir)
        self.decisions: list[Decision] = []

    def evaluate(self, action: dict) -> dict:
        """Evaluate an action against constitutional rules and policies.

        Args:
            action: Action request. Expected fields:
                - goal (str): What the action intends to achieve
                - scope (str): Scope of the action
                - risk (str): Risk level — 'low', 'medium', 'high', 'critical'
                - audit_log (bool or dict): Whether audit logging is enabled
                - action_type (str, optional): Type of action
                - agent_id (str, optional): ID of the requesting agent
                - authority (str, optional): Authority level of the agent

        Returns:
            Decision dict with outcome, reason, violations, requirements, etc.
        """
        ctx = EvaluationContext(action=action)

        # --- Phase 1: Required fields check ---
        required_fields = ["goal", "scope", "risk", "audit_log"]
        missing = [f for f in required_fields if not action.get(f)]
        if missing:
            decision = Decision(
                evaluation_id=ctx.evaluation_id,
                outcome=DecisionOutcome.DENY,
                reason="missing_required_fields",
                details=f"Missing required fields: {missing}",
                constitution_version=self.version,
                requirements=[{"field": f, "status": "missing"} for f in missing],
            )
            self.decisions.append(decision)
            return self._decision_to_dict(decision)

        # --- Phase 2: Restricted action check ---
        action_type = action.get("action_type", "")
        restricted = _RESTRICTED_ACTIONS.get(action_type)
        if restricted:
            escalation = restricted["escalation"]
            decision = Decision(
                evaluation_id=ctx.evaluation_id,
                outcome=DecisionOutcome.REVIEW,
                reason="restricted_action",
                details=restricted["reason"],
                constitution_version=self.version,
                violations=[
                    {
                        "type": "restricted_action",
                        "article": restricted["article"],
                        "reason": restricted["reason"],
                    }
                ],
                policy_actions=[
                    {
                        "escalation": escalation,
                        "action": self.policies.get_threat_action("critical"),
                    }
                ],
                matched_articles=[restricted["article"]],
            )
            self.decisions.append(decision)
            return self._decision_to_dict(decision)

        # --- Phase 3: Constitution MUST NOT check ---
        must_not_hits = self.constitution.check_action(action)
        prohibition_hits = [h for h in must_not_hits if h["type"] == "prohibition"]

        # --- Phase 4: Policy-based checks ---
        policy_violations = self._check_policies(action, ctx)
        policy_reqs = self._check_policy_requirements(action, ctx)

        # --- Phase 5: Risk-based evaluation ---
        risk_level = action.get("risk", "medium").lower()
        threat_action = self.policies.get_threat_action(risk_level)
        threat_escalation = self.policies.get_threat_escalation(risk_level)

        # --- Phase 6: Core principle checks ---
        principle_violations = self._check_core_principles(action, ctx)

        # Combine all violations and requirements
        all_violations = (
            prohibition_hits + policy_violations + principle_violations + ctx.violations
        )
        all_requirements = (
            [h for h in must_not_hits if h["type"] == "requirement"]
            + policy_reqs
            + ctx.requirements
        )

        # --- Phase 7: Determine outcome ---
        outcome, reason, details = self._determine_outcome(
            action=action,
            violations=all_violations,
            requirements=all_requirements,
            risk_level=risk_level,
            threat_action=threat_action,
            threat_escalation=threat_escalation,
            warnings=ctx.warnings,
        )

        # Gather matched articles and policies
        matched_articles = list({v.get("article", "") for v in all_violations if v.get("article")})
        matched_policies = list({v.get("policy", "") for v in all_violations if v.get("policy")})

        decision = Decision(
            evaluation_id=ctx.evaluation_id,
            outcome=outcome,
            reason=reason,
            details=details,
            constitution_version=self.version,
            violations=all_violations,
            requirements=all_requirements,
            policy_actions=[
                {
                    "threat_level": risk_level,
                    "action": threat_action,
                    "escalation": threat_escalation,
                }
            ],
            matched_articles=matched_articles,
            matched_policies=matched_policies,
        )

        self.decisions.append(decision)
        return self._decision_to_dict(decision)

    def _check_policies(self, action: dict, ctx: EvaluationContext) -> list[dict]:
        """Check action against YAML policy rules."""
        violations = []
        risk = action.get("risk", "medium").lower()

        # Security policy checks
        sec = self.policies.get_security_policy()
        if sec:
            # Unknown access blocked rule
            if (
                self.policies.is_rule_enabled("security_policy", "unknown_access_blocked")
                and action.get("agent_id") == "unknown"
            ):
                violations.append(
                    {
                        "type": "policy_violation",
                        "policy": "security_policy",
                        "rule": "unknown_access_blocked",
                        "reason": "Unknown agents cannot be granted access",
                    }
                )

            # Least privilege
            if (
                self.policies.is_rule_enabled("security_policy", "least_privilege")
                and action.get("authority") == "unlimited"
            ):
                violations.append(
                    {
                        "type": "policy_violation",
                        "policy": "security_policy",
                        "rule": "least_privilege",
                        "reason": "Unlimited authority violates least privilege principle",
                    }
                )

            # Audit logging required
            if self.policies.is_requirement_met(
                "security_policy", "audit_logging"
            ) and not action.get("audit_log"):
                violations.append(
                    {
                        "type": "policy_violation",
                        "policy": "security_policy",
                        "rule": "audit_logging",
                        "reason": "Security policy requires audit logging",
                    }
                )

            # Risk escalation to REVIEW for critical
            if risk == "critical":
                threat = sec.threat_levels.get("critical")
                if threat and threat.escalation == "human_review":
                    violations.append(
                        {
                            "type": "policy_escalation",
                            "policy": "security_policy",
                            "escalation": "human_review",
                            "reason": "Critical risk requires human review",
                        }
                    )

        # Evolution policy checks
        if action.get("action_type", "").startswith("evolution"):
            evo = self.policies.get_evolution_policy()
            if evo:
                restrictions = self.policies.get_evolution_restrictions()
                for restriction_name, restriction_value in restrictions.items():
                    if restriction_value in ("prohibited", "blocked"):
                        if restriction_name in str(action.get("action_type", "")):
                            violations.append(
                                {
                                    "type": "policy_violation",
                                    "policy": "evolution_policy",
                                    "rule": restriction_name,
                                    "reason": f"Evolution restriction: {restriction_name} is {restriction_value}",
                                }
                            )

                # Constitutional validation required
                if self.policies.is_requirement_met(
                    "evolution_policy", "constitutional_validation"
                ):
                    if not action.get("constitutional_check"):
                        violations.append(
                            {
                                "type": "policy_violation",
                                "policy": "evolution_policy",
                                "rule": "constitutional_validation",
                                "reason": "Evolution actions require constitutional validation",
                            }
                        )

        # Federation policy checks
        if action.get("action_type", "") in ("federate", "sync", "state_exchange"):
            fed = self.policies.get_federation_policy()
            if fed:
                if self.policies.is_rule_enabled(
                    "federation_policy", "verified_nodes_only"
                ) and not action.get("node_verified"):
                    violations.append(
                        {
                            "type": "policy_violation",
                            "policy": "federation_policy",
                            "rule": "verified_nodes_only",
                            "reason": "Federation requires verified nodes",
                        }
                    )

        return violations

    def _check_policy_requirements(self, action: dict, ctx: EvaluationContext) -> list[dict]:
        """Check that policy requirements are satisfied."""
        reqs = []

        # Security policy requirements
        sec = self.policies.get_security_policy()
        if sec:
            for req in sec.requirements:
                if req.name == "access_control" and req.value:
                    if not action.get("agent_id"):
                        reqs.append(
                            {
                                "policy": "security_policy",
                                "requirement": "access_control",
                                "status": "not_satisfied",
                                "detail": "Agent ID required for access control",
                            }
                        )

                if req.name == "node_verification" and req.value:
                    if action.get("action_type") in (
                        "federate",
                        "sync",
                    ) and not action.get("node_verified"):
                        reqs.append(
                            {
                                "policy": "security_policy",
                                "requirement": "node_verification",
                                "status": "not_satisfied",
                                "detail": "Node verification required for federation actions",
                            }
                        )

        # Evolution policy requirements
        if action.get("action_type", "").startswith("evolution"):
            evo = self.policies.get_evolution_policy()
            if evo:
                for req in evo.requirements:
                    if req.name == "testing_before_deployment" and req.value:
                        if not action.get("testing_completed"):
                            reqs.append(
                                {
                                    "policy": "evolution_policy",
                                    "requirement": "testing_before_deployment",
                                    "status": "not_satisfied",
                                    "detail": "Testing must complete before deployment",
                                }
                            )
                    if req.name == "rollback_capability" and str(req.value) == "required":
                        if not action.get("rollback_plan"):
                            reqs.append(
                                {
                                    "policy": "evolution_policy",
                                    "requirement": "rollback_capability",
                                    "status": "not_satisfied",
                                    "detail": "Rollback plan required for evolution actions",
                                }
                            )

        return reqs

    def _check_core_principles(self, action: dict, ctx: EvaluationContext) -> list[dict]:
        """Check action against the 6 core constitutional principles."""
        violations = []

        # Principle 1: Limited Autonomy — requires goal, scope, risk, audit
        if not action.get("goal"):
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "limited_autonomy",
                    "detail": "Every autonomous action requires a clear goal",
                }
            )
        if not action.get("scope"):
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "limited_autonomy",
                    "detail": "Every autonomous action requires a defined scope",
                }
            )
        if not action.get("risk"):
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "limited_autonomy",
                    "detail": "Every autonomous action requires risk assessment",
                }
            )
        if not action.get("audit_log"):
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "limited_autonomy",
                    "detail": "Every autonomous action requires audit logging",
                }
            )

        # Principle 3: Memory Separation — personal data should not be shared
        if action.get("memory_type") == "personal" and action.get("share"):
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "memory_separation",
                    "detail": "Personal memory MUST NOT be shared (federated)",
                }
            )

        # Principle 5: Controlled Evolution — evolution needs stages
        if action.get("action_type", "").startswith("evolution") and not action.get(
            "evolution_stage"
        ):
            evo_stages = self.policies.get_evolution_stages()
            violations.append(
                {
                    "type": "core_principle_violation",
                    "principle": "controlled_evolution",
                    "detail": f"Evolution actions must follow the pipeline: {evo_stages}",
                }
            )

        return violations

    def _determine_outcome(
        self,
        action: dict,
        violations: list[dict],
        requirements: list[dict],
        risk_level: str,
        threat_action: Optional[str],
        threat_escalation: Optional[str],
        warnings: list[str],
    ) -> tuple[DecisionOutcome, str, str]:
        """Determine the final evaluation outcome."""
        # Any hard violations → DENY
        hard_violations = [
            v
            for v in violations
            if v.get("type") in ("policy_violation", "core_principle_violation", "prohibition")
            and v.get("type") != "policy_escalation"
        ]
        if hard_violations:
            reasons = [v.get("reason", v.get("detail", "")) for v in hard_violations]
            return (
                DecisionOutcome.DENY,
                "constitutional_or_policy_violation",
                "; ".join(reasons[:3]),
            )

        # Escalation violations → REVIEW
        escalation_hits = [
            v for v in violations if v.get("type") in ("policy_escalation", "restricted_action")
        ]
        if escalation_hits:
            reasons = [v.get("reason", "") for v in escalation_hits]
            return (
                DecisionOutcome.REVIEW,
                "escalation_required",
                "; ".join(reasons),
            )

        # Unmet requirements → REVIEW
        unmet = [r for r in requirements if r.get("status") == "not_satisfied"]
        if unmet:
            details = "; ".join(r.get("detail", "") for r in unmet[:3])
            return (
                DecisionOutcome.REVIEW,
                "unmet_requirements",
                details,
            )

        # High risk → REVIEW
        if risk_level in ("high", "critical"):
            return (
                DecisionOutcome.REVIEW,
                "risk_review",
                f"Risk level '{risk_level}' requires review. "
                f"Policy action: {threat_action}, escalation: {threat_escalation}",
            )

        # All checks passed → ALLOW
        return (
            DecisionOutcome.ALLOW,
            "constitutional_compliance",
            "Action complies with constitutional principles and all policies",
        )

    def _decision_to_dict(self, decision: Decision) -> dict:
        """Convert a Decision dataclass to a plain dict."""
        return {
            "evaluation_id": decision.evaluation_id,
            "decision": decision.outcome.value,
            "reason": decision.reason,
            "details": decision.details,
            "constitution_version": decision.constitution_version,
            "violations": decision.violations,
            "requirements": decision.requirements,
            "policy_actions": decision.policy_actions,
            "timestamp": decision.timestamp,
            "matched_articles": decision.matched_articles,
            "matched_policies": decision.matched_policies,
        }

    def history(self) -> list[dict]:
        """Return full decision history as dicts."""
        return [self._decision_to_dict(d) for d in self.decisions]

    def stats(self) -> dict:
        """Return engine statistics."""
        constitution_stats = self.constitution.stats()
        policy_stats = self.policies.stats()

        outcome_counts = {"ALLOW": 0, "DENY": 0, "REVIEW": 0}
        for d in self.decisions:
            outcome_counts[d.outcome.value] += 1

        return {
            "version": self.version,
            "total_evaluations": len(self.decisions),
            "outcomes": outcome_counts,
            "constitution": constitution_stats,
            "policies": policy_stats,
        }
