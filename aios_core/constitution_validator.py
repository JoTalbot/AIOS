"""AIOS Constitution Validator v3.0.0

Validates actions against real constitutional rules loaded from markdown
articles and YAML policies. Replaces the v2.1.1 hardcoded stub.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .constitution_loader import (
    ConstitutionLoader,
    ConstitutionalRule,
    ObligationLevel,
)
from .policy_loader import PolicyLoader


@dataclass
class ValidationResult:
    """Detailed result of a single validation check."""
    valid: bool
    category: str  # e.g. "field", "principle", "policy", "constitution"
    code: str  # machine-readable code e.g. "missing_goal"
    message: str
    severity: str  # "error" or "warning"
    article_id: Optional[str] = None
    policy_name: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report for an action."""
    valid: bool
    errors: list[ValidationResult] = field(default_factory=list)
    warnings: list[ValidationResult] = field(default_factory=list)
    checked_rules_count: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ConstitutionValidator:
    """Validates constitutional compliance of AIOS operations.

    Uses the loaded constitution and policies to perform deep validation,
    going beyond simple field presence checks to verify:
    - Required fields (Principle 1: Limited Autonomy)
    - Core principle compliance
    - Policy requirement satisfaction
    - Constitution MUST/SHOULD rule applicability
    """

    def __init__(
        self,
        constitution_dir: Optional[str] = None,
        policies_dir: Optional[str] = None,
    ):
        self.version = "3.0.0"
        self.constitution = ConstitutionLoader(constitution_dir)
        self.policies = PolicyLoader(policies_dir)
        self.validations: list[ValidationReport] = []

    def validate(self, action: dict) -> dict:
        """Validate an action against constitutional rules and policies.

        Args:
            action: Action to validate with expected fields:
                - goal, scope, risk, audit_log (required)
                - action_type, agent_id, authority (optional)

        Returns:
            Validation report dict with valid, errors, warnings, details.
        """
        report = ValidationReport(valid=True)
        results: list[ValidationResult] = []

        # --- 1. Required fields (Core Principle 1: Limited Autonomy) ---
        results.extend(self._validate_required_fields(action))

        # --- 2. Risk assessment validity ---
        results.extend(self._validate_risk(action))

        # --- 3. Core principle compliance ---
        results.extend(self._validate_core_principles(action))

        # --- 4. Policy compliance ---
        results.extend(self._validate_policy_compliance(action))

        # --- 5. Constitution rule relevance check ---
        relevant_rules = self.constitution.check_action(action)
        report.checked_rules_count = len(relevant_rules)
        results.extend(self._validate_constitution_relevance(action, relevant_rules))

        # Separate into errors and warnings
        for r in results:
            if r.severity == "error":
                report.errors.append(r)
                report.valid = False
            else:
                report.warnings.append(r)

        self.validations.append(report)
        return self._report_to_dict(report)

    def _validate_required_fields(self, action: dict) -> list[ValidationResult]:
        """Validate required action fields (Limited Autonomy principle)."""
        results = []
        field_checks = {
            "goal": "Every autonomous action requires a clear goal",
            "scope": "Every autonomous action requires a defined scope",
            "risk": "Every autonomous action requires risk assessment",
            "audit_log": "Every autonomous action requires audit logging",
        }

        for field_name, message in field_checks.items():
            value = action.get(field_name)
            if not value:
                results.append(ValidationResult(
                    valid=False,
                    category="field",
                    code=f"missing_{field_name}",
                    message=f"Missing required field: {field_name}. {message}",
                    severity="error",
                ))

        return results

    def _validate_risk(self, action: dict) -> list[ValidationResult]:
        """Validate risk assessment fields."""
        results = []
        risk = action.get("risk", "")

        if risk:
            valid_levels = {"low", "medium", "high", "critical"}
            if risk.lower() not in valid_levels:
                results.append(ValidationResult(
                    valid=False,
                    category="risk",
                    code="invalid_risk_level",
                    message=f"Invalid risk level '{risk}'. "
                           f"Must be one of: {valid_levels}",
                    severity="error",
                ))

            # High/critical risk without authority justification
            if risk.lower() in ("high", "critical") and not action.get("authority"):
                results.append(ValidationResult(
                    valid=True,
                    category="risk",
                    code="high_risk_no_authority",
                    message=f"Risk level '{risk}' specified but no authority field provided",
                    severity="warning",
                ))

        return results

    def _validate_core_principles(self, action: dict) -> list[ValidationResult]:
        """Validate against the 6 core constitutional principles."""
        results = []

        # Principle 2: Minimal Force
        # If alternatives exist, verify the least disruptive is chosen
        if action.get("alternatives") and not action.get("minimal_force_justified"):
            results.append(ValidationResult(
                valid=True,
                category="principle",
                code="minimal_force",
                message="Alternatives exist but minimal force justification is missing "
                       "(Principle 2: Minimal Force)",
                severity="warning",
            ))

        # Principle 3: Memory Separation
        if action.get("memory_type") == "personal" and action.get("share"):
            results.append(ValidationResult(
                valid=False,
                category="principle",
                code="memory_separation_violation",
                message="Personal memory MUST NOT be shared "
                       "(Principle 3: Memory Separation)",
                severity="error",
            ))

        if action.get("memory_type") not in (None, "personal", "operational", "constitutional"):
            results.append(ValidationResult(
                valid=True,
                category="principle",
                code="unknown_memory_type",
                message=f"Unknown memory type '{action.get('memory_type')}'. "
                       f"Valid types: personal, operational, constitutional",
                severity="warning",
            ))

        # Principle 4: Federated Operation
        if action.get("action_type") in ("federate", "sync", "state_exchange"):
            if not action.get("offline_log"):
                results.append(ValidationResult(
                    valid=True,
                    category="principle",
                    code="federation_logging",
                    message="Federation actions should enable offline logging "
                           "(Principle 4: Federated Operation)",
                    severity="warning",
                ))

        # Principle 5: Controlled Evolution
        if action.get("action_type", "").startswith("evolution"):
            evo_stages = self.policies.get_evolution_stages()
            stage = action.get("evolution_stage")
            if stage and evo_stages and stage not in evo_stages:
                results.append(ValidationResult(
                    valid=False,
                    category="principle",
                    code="invalid_evolution_stage",
                    message=f"Invalid evolution stage '{stage}'. "
                           f"Valid stages: {evo_stages}",
                    severity="error",
                ))

        # Principle 6: Uncertainty Handling
        if action.get("uncertainty_detected") and not action.get("reversible"):
            results.append(ValidationResult(
                valid=True,
                category="principle",
                code="uncertainty_reversibility",
                message="Uncertainty detected but action is not marked as reversible "
                       "(Principle 6: Uncertainty Handling)",
                severity="warning",
            ))

        return results

    def _validate_policy_compliance(self, action: dict) -> list[ValidationResult]:
        """Validate action against loaded YAML policies."""
        results = []

        # Security policy requirements
        sec = self.policies.get_security_policy()
        if sec:
            for req in sec.requirements:
                if req.name == "access_control" and req.value:
                    if not action.get("agent_id"):
                        results.append(ValidationResult(
                            valid=True,
                            category="policy",
                            code="security_access_control",
                            message="Security policy requires access control — "
                                   "agent_id field is missing",
                            severity="warning",
                            policy_name="security_policy",
                        ))

                if req.name == "audit_logging" and req.value:
                    if not action.get("audit_log"):
                        results.append(ValidationResult(
                            valid=False,
                            category="policy",
                            code="security_audit_logging",
                            message="Security policy mandates audit logging",
                            severity="error",
                            policy_name="security_policy",
                        ))

            for rule in sec.rules:
                if rule.name == "least_privilege" and rule.enabled:
                    if action.get("authority") == "unlimited":
                        results.append(ValidationResult(
                            valid=False,
                            category="policy",
                            code="security_least_privilege",
                            message="Security policy: least privilege rule "
                                   "forbids unlimited authority",
                            severity="error",
                            policy_name="security_policy",
                        ))

        # Evolution policy requirements
        if action.get("action_type", "").startswith("evolution"):
            evo = self.policies.get_evolution_policy()
            if evo:
                for req in evo.requirements:
                    if req.name == "testing_before_deployment" and req.value:
                        if not action.get("testing_completed"):
                            results.append(ValidationResult(
                                valid=True,
                                category="policy",
                                code="evolution_testing",
                                message="Evolution policy requires testing before deployment",
                                severity="warning",
                                policy_name="evolution_policy",
                            ))

                    if req.name == "constitutional_validation" and req.value:
                        if not action.get("constitutional_check"):
                            results.append(ValidationResult(
                                valid=True,
                                category="policy",
                                code="evolution_constitutional_check",
                                message="Evolution policy requires constitutional validation",
                                severity="warning",
                                policy_name="evolution_policy",
                            ))

                # Check restrictions
                restrictions = self.policies.get_evolution_restrictions()
                for rname, rvalue in restrictions.items():
                    if rvalue in ("prohibited", "blocked"):
                        # Flag as warning — actual enforcement is in ConstitutionEngine
                        results.append(ValidationResult(
                            valid=True,
                            category="policy",
                            code=f"evolution_restriction_{rname}",
                            message=f"Evolution policy: {rname} is {rvalue}",
                            severity="warning",
                            policy_name="evolution_policy",
                        ))

        # Federation policy
        fed = self.policies.get_federation_policy()
        if fed and action.get("action_type") in ("federate", "sync"):
            if self.policies.is_rule_enabled("federation_policy", "verified_nodes_only"):
                if not action.get("node_verified"):
                    results.append(ValidationResult(
                        valid=True,
                        category="policy",
                        code="federation_verified_nodes",
                        message="Federation policy requires verified nodes",
                        severity="warning",
                        policy_name="federation_policy",
                    ))

        return results

    def _validate_constitution_relevance(
        self, action: dict, relevant_rules: list[dict]
    ) -> list[ValidationResult]:
        """Flag constitution rules that may be relevant to the action."""
        results = []

        for rule_info in relevant_rules:
            if rule_info["type"] == "prohibition":
                results.append(ValidationResult(
                    valid=True,
                    category="constitution",
                    code=f"constitution_prohibition_{rule_info['article']}",
                    message=f"Relevant constitutional prohibition "
                           f"({rule_info['article']}): {rule_info['rule'][:100]}",
                    severity="warning",
                    article_id=rule_info["article"],
                ))

        return results

    def _report_to_dict(self, report: ValidationReport) -> dict:
        """Convert a ValidationReport to a plain dict."""
        return {
            "valid": report.valid,
            "errors": [
                {
                    "category": e.category,
                    "code": e.code,
                    "message": e.message,
                    "article": e.article_id,
                    "policy": e.policy_name,
                }
                for e in report.errors
            ],
            "warnings": [
                {
                    "category": w.category,
                    "code": w.code,
                    "message": w.message,
                    "article": w.article_id,
                    "policy": w.policy_name,
                }
                for w in report.warnings
            ],
            "error_count": len(report.errors),
            "warning_count": len(report.warnings),
            "checked_rules_count": report.checked_rules_count,
            "timestamp": report.timestamp,
        }

    def report(self) -> dict:
        """Generate aggregate validation report."""
        total = len(self.validations)
        valid = sum(1 for v in self.validations if v.valid)
        total_errors = sum(len(v.errors) for v in self.validations)
        total_warnings = sum(len(v.warnings) for v in self.validations)

        return {
            "total_validations": total,
            "valid": valid,
            "invalid": total - valid,
            "success_rate": valid / total if total > 0 else 0,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "validator_version": self.version,
        }