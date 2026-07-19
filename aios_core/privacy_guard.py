"""AIOS Privacy Guard v3.0.0

Enforces memory access control and data classification rules.
Pure in-memory rule engine (no database dependency).

Core Principle 3 (Memory Separation) enforcement:
- Personal memory CANNOT be shared (federated)
- Constitutional memory is read-only
- Operational memory can be shared with verified agents
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


class PrivacyGuard:
    """Manages privacy protection and data access control.

    v3.0.0: Full implementation with configurable rules, access log,
    and comprehensive privacy checks.
    """

    def __init__(self):
        self.version = "3.0.0"
        self._access_log: list[dict] = []

        # Default classification rules
        self._rules: list[dict] = [
            # Personal data: read-only, never shared
            {
                "classification": "personal",
                "actions_allowed": ["read"],
                "share_allowed": False,
                "description": "Personal data is user-controlled and never federated",
            },
            # Constitutional data: read-only, never modified, never shared
            {
                "classification": "constitutional",
                "actions_allowed": ["read"],
                "share_allowed": False,
                "description": "Constitutional data is immutable and read-only",
            },
            # Operational data: read/write for verified agents, shareable
            {
                "classification": "operational",
                "actions_allowed": ["read", "write", "delete"],
                "share_allowed": True,
                "share_requires_verification": True,
                "description": "Operational data can be shared with verified agents",
            },
        ]

    def can_access(
        self,
        agent_id: str,
        memory_category: str,
        action: str,
    ) -> dict:
        """Check if an agent can access a memory category.

        Args:
            agent_id: The agent requesting access.
            memory_category: personal, operational, or constitutional.
            action: The action requested (read, write, delete, share).

        Returns:
            Dict with 'allowed', 'reason', and classification info.
        """
        result = self._check_rules(memory_category, action, agent_id)
        self._access_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "memory_category": memory_category,
            "action": action,
            **result,
        })
        return result

    def can_share(self, data_classification: str, target: str) -> dict:
        """Check if data of a given classification can be shared.

        Args:
            data_classification: The data classification level.
            target: The target recipient.

        Returns:
            Dict with 'allowed' and 'reason'.
        """
        rule = self._find_rule(data_classification)

        if rule is None:
            result = {
                "allowed": False,
                "reason": f"Unknown classification: {data_classification}",
                "classification": data_classification,
            }
            self._access_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": target,
                "memory_category": data_classification,
                "action": "share",
                **result,
            })
            return result

        share_allowed = rule.get("share_allowed", False)
        requires_verification = rule.get("share_requires_verification", False)

        if not share_allowed:
            result = {
                "allowed": False,
                "reason": f"{data_classification} data cannot be shared",
                "classification": data_classification,
            }
        elif requires_verification and target == "unverified":
            result = {
                "allowed": False,
                "reason": f"{data_classification} data requires verified target",
                "classification": data_classification,
            }
        else:
            result = {
                "allowed": True,
                "reason": f"{data_classification} data sharing approved",
                "classification": data_classification,
            }

        self._access_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": target,
            "memory_category": data_classification,
            "action": "share",
            **result,
        })
        return result

    def check_request(self, request: dict) -> dict:
        """Comprehensive privacy check for a data access request.

        Args:
            request: Dict with agent_id, memory_category, action, and
                     optional target (for sharing).

        Returns:
            Dict with 'allowed', 'reason', and 'details'.
        """
        agent_id = request.get("agent_id", "unknown")
        memory_category = request.get("memory_category", "operational")
        action = request.get("action", "read")
        target = request.get("target")

        # Check basic access
        access_result = self.can_access(agent_id, memory_category, action)

        if not access_result["allowed"]:
            return {
                "allowed": False,
                "reason": access_result["reason"],
                "details": access_result,
                "agent_id": agent_id,
                "memory_category": memory_category,
                "action": action,
            }

        # If sharing, also check share permission
        if action == "share" and target:
            share_result = self.can_share(memory_category, target)
            if not share_result["allowed"]:
                return {
                    "allowed": False,
                    "reason": share_result["reason"],
                    "details": share_result,
                    "agent_id": agent_id,
                    "memory_category": memory_category,
                    "action": action,
                    "target": target,
                }

        return {
            "allowed": True,
            "reason": f"Access granted: {action} on {memory_category} for {agent_id}",
            "details": access_result,
            "agent_id": agent_id,
            "memory_category": memory_category,
            "action": action,
        }

    def get_access_log(self) -> list[dict]:
        """Get the full access audit trail.

        Returns:
            List of access check records.
        """
        return list(self._access_log)

    def add_rule(self, rule: dict) -> None:
        """Add a custom privacy rule.

        Args:
            rule: Dict with classification, actions_allowed, share_allowed, etc.
        """
        self._rules.append(rule)

    def _find_rule(self, classification: str) -> Optional[dict]:
        """Find the rule for a classification level."""
        for rule in self._rules:
            if rule.get("classification") == classification:
                return rule
        return None

    def _check_rules(
        self,
        memory_category: str,
        action: str,
        agent_id: str,
    ) -> dict:
        """Check rules for a given access request."""
        rule = self._find_rule(memory_category)

        if rule is None:
            return {
                "allowed": False,
                "reason": f"Unknown memory category: {memory_category}",
                "classification": memory_category,
            }

        allowed_actions = rule.get("actions_allowed", [])
        if action not in allowed_actions:
            return {
                "allowed": False,
                "reason": f"Action '{action}' not allowed on {memory_category} memory",
                "classification": memory_category,
            }

        return {
            "allowed": True,
            "reason": f"Access granted: {action} on {memory_category}",
            "classification": memory_category,
        }

    def stats(self) -> dict:
        """Return privacy guard statistics."""
        total_checks = len(self._access_log)
        allowed_count = sum(1 for log in self._access_log if log.get("allowed", False))
        denied_count = total_checks - allowed_count

        return {
            "version": self.version,
            "total_access_checks": total_checks,
            "allowed": allowed_count,
            "denied": denied_count,
            "rules_count": len(self._rules),
            "storage": "memory",
        }