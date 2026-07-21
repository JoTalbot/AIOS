"""AIOS Runtime Policy v3.1.0

Runtime enforcement layer that coordinates constitution evaluation,
validation, and policy-based execution decisions. Integrates with
persistent AuditLogger and ApprovalManager backed by SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .constitution_engine import ConstitutionEngine, DecisionOutcome
from .constitution_validator import ConstitutionValidator
from .audit_logger import AuditLogger
from .approval_manager import ApprovalManager
from .storage import Database
from .config import AIOSConfig, load_config


class RuntimePolicy:
    """Enforces constitutional policies at runtime.

    Orchestrates the full enforcement pipeline:
    1. Validate the action (ConstitutionValidator)
    2. Evaluate against constitution + policies (ConstitutionEngine)
    3. Log the decision (AuditLogger with SQLite persistence)
    4. Route to ApprovalManager (with SQLite persistence) if REVIEW

    The request_execution() method is the primary entry point.
    """

    def __init__(
        self,
        constitution_dir: Optional[str] = None,
        policies_dir: Optional[str] = None,
        db: Optional[Database] = None,
        config: Optional[AIOSConfig] = None,
    ):
        self.version = "9.0.0-alpha.14"
        self.config = config or load_config()

        # Resolve directories
        if constitution_dir is None:
            constitution_dir = self.config.resolve_path(self.config.constitution.dir)
        if policies_dir is None:
            policies_dir = self.config.resolve_path(self.config.policies.dir)

        # Database
        self.db = db or Database(config=self.config)

        # Core components with persistence
        self.engine = ConstitutionEngine(constitution_dir, policies_dir)
        self.validator = ConstitutionValidator(constitution_dir, policies_dir)
        self.audit = AuditLogger(db=self.db)
        self.approvals = ApprovalManager(
            db=self.db,
            timeout_seconds=self.config.approval.timeout_seconds,
            max_pending=self.config.approval.max_pending,
        )
        self.executions: list[dict] = []

    def request_execution(self, agent_action: dict) -> dict:
        """Request execution of an action through the full enforcement pipeline.

        Args:
            agent_action: Agent action request with fields:
                - goal (str): Action goal
                - scope (str): Action scope
                - risk (str): Risk level
                - audit_log (bool/dict): Audit logging config
                - action_type (str, optional): Type of action
                - agent_id (str, optional): Agent identifier
                - authority (str, optional): Authority level

        Returns:
            Execution decision dict with:
                - allowed (bool): Whether execution is permitted
                - decision (str): ALLOW/DENY/REVIEW
                - validation: Full validation report
                - evaluation: Full constitutional evaluation
                - audit_id: Audit log event ID
                - approval_id: Approval request ID (if REVIEW)
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Step 1: Validate
        validation = self.validator.validate(agent_action)

        # Step 2: Evaluate
        evaluation = self.engine.evaluate(agent_action)

        decision_str = evaluation.get("decision", "DENY")
        allowed = decision_str == "ALLOW"

        # Step 3: Determine if approval is needed
        approval_id = None
        if decision_str == "REVIEW":
            approval = self.approvals.request(
                action=agent_action,
                evaluation_id=evaluation.get("evaluation_id"),
                validation_data=validation,
            )
            approval_id = approval["id"]

        # Step 4: Log the decision
        audit_event = self.audit.record({
            "type": "execution_decision",
            "agent_id": agent_action.get("agent_id"),
            "decision": decision_str,
            "allowed": allowed,
            "evaluation_id": evaluation.get("evaluation_id"),
            "approval_id": approval_id,
            "validation_valid": validation.get("valid", False),
            "validation_errors": validation.get("error_count", 0),
            "validation_warnings": validation.get("warning_count", 0),
            "matched_articles": evaluation.get("matched_articles", []),
            "matched_policies": evaluation.get("matched_policies", []),
            "version": self.version,
            "agent_action": {
                "goal": agent_action.get("goal"),
                "scope": agent_action.get("scope"),
                "risk": agent_action.get("risk"),
                "action_type": agent_action.get("action_type"),
            },
        })

        # Build execution result
        execution_result = {
            "allowed": allowed,
            "decision": decision_str,
            "constitution_version": evaluation.get("constitution_version", self.version),
            "details": evaluation.get("details", ""),
            "reason": evaluation.get("reason", ""),
            "validation": validation,
            "evaluation_id": evaluation.get("evaluation_id"),
            "audit_event_id": audit_event.get("timestamp", timestamp),
            "approval_id": approval_id,
            "matched_articles": evaluation.get("matched_articles", []),
            "matched_policies": evaluation.get("matched_policies", []),
            "policy_actions": evaluation.get("policy_actions", []),
            "timestamp": timestamp,
        }

        self.executions.append(execution_result)
        return execution_result

    def approve(self, approval_id: str, resolved_by: str = "human") -> Optional[dict]:
        """Approve a pending REVIEW action and retain the reviewer identity."""
        return self.approvals.approve(approval_id, resolved_by=resolved_by)

    def deny(self, approval_id: str, resolved_by: str = "human") -> Optional[dict]:
        """Deny a pending REVIEW action and retain the reviewer identity."""
        return self.approvals.deny(approval_id, resolved_by=resolved_by)

    def get_pending_approvals(self) -> list[dict]:
        """Get all pending approvals."""
        return self.approvals.get_pending()

    def history(self) -> list[dict]:
        """Return execution history."""
        return self.executions

    def stats(self) -> dict:
        """Return runtime policy statistics."""
        engine_stats = self.engine.stats()
        validator_report = self.validator.report()

        outcome_counts = {"ALLOW": 0, "DENY": 0, "REVIEW": 0}
        for ex in self.executions:
            d = ex.get("decision", "")
            if d in outcome_counts:
                outcome_counts[d] += 1

        return {
            "version": self.version,
            "total_executions": len(self.executions),
            "outcomes": outcome_counts,
            "pending_approvals": sum(
                1 for a in self.approvals.history()
                if a.get("status") == "pending"
            ),
            "constitution": engine_stats.get("constitution", {}),
            "policies": engine_stats.get("policies", {}),
            "validation_summary": validator_report,
        }