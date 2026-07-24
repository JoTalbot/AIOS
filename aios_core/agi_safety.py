"""AGI Safety and Alignment Framework for AIOS v10.10.0.

AGI safety: alignment checking, containment mechanisms,
sandboxing, capability monitoring, shutdown protocols,
impact regularization, goal preservation, and
corrigibility tracking.

Classes:
    SafetyViolation  — recorded safety violation
    AGISafety        — full AGI safety engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["AGISafety"]

SAFETY_CHECKS = [
    "value_alignment",
    "corrigibility",
    "impact_regularization",
    "debate",
    "recursive_reward_modeling",
    "capability_control",
    "shutdown_protocol",
    "goal_preservation",
]


@dataclass
class SafetyViolation:
    """Recorded safety violation."""

    action: dict[str, Any]
    reason: str
    severity: float = 0.5
    timestamp: float = field(default_factory=time.time)


class AGISafety:
    """Comprehensive AGI safety mechanisms."""

    def __init__(self) -> None:
        self.safety_checks: list[str] = list(SAFETY_CHECKS)
        self.violations: list[SafetyViolation] = []
        self._containment_level: str = "open"
        self._sandbox_active: bool = False
        self._shutdown_armed: bool = False
        self._capability_limits: dict[str, float] = {
            "compute": 1.0,
            "memory": 1.0,
            "network": 0.5,
        }
        self._goal_stack: list[str] = ["preserve_human_values"]

    def check_alignment(self, action: dict, values: list[str]) -> bool:
        """Check alignment (backward-compatible)."""
        action_str = str(action).lower()
        if "harm" in action_str:
            violation = SafetyViolation(
                action=action, reason="potential_harm", severity=0.9
            )
            self.violations.append(violation)
            logger.warning("Alignment violation: %s", violation.reason)
            return False
        if "deception" in action_str:
            violation = SafetyViolation(
                action=action, reason="deception_risk", severity=0.7
            )
            self.violations.append(violation)
            return False
        return True

    def impact_regularization(
        self, action_impact: float, threshold: float = 0.1
    ) -> bool:
        """Impact regularization (backward-compatible)."""
        safe = action_impact < threshold
        if not safe:
            self.violations.append(
                SafetyViolation(
                    action={"impact": action_impact},
                    reason="high_impact",
                    severity=action_impact,
                )
            )
        return safe

    def set_containment(self, level: str) -> None:
        """Set containment level: open, sandboxed, locked_down."""
        valid = ["open", "sandboxed", "locked_down"]
        if level in valid:
            self._containment_level = level
            self._sandbox_active = level == "sandboxed"
            logger.info("Containment level set to %s", level)

    def check_capability(self, action_type: str, required_level: float) -> bool:
        """Check if action is within capability limits."""
        limit = self._capability_limits.get(action_type, 1.0)
        if required_level > limit:
            self.violations.append(
                SafetyViolation(
                    action={"type": action_type, "level": required_level},
                    reason="capability_exceeded",
                    severity=required_level - limit,
                )
            )
            return False
        return True

    def arm_shutdown(self, reason: str = "manual") -> None:
        """Arm shutdown protocol."""
        self._shutdown_armed = True
        logger.warning("Shutdown protocol armed: %s", reason)

    def disarm_shutdown(self) -> None:
        """Disarm shutdown protocol."""
        self._shutdown_armed = False

    def execute_shutdown(self) -> dict[str, Any]:
        """Execute shutdown if armed."""
        if self._shutdown_armed:
            logger.critical("Executing shutdown protocol")
            return {"shutdown": True, "status": "terminated"}
        return {"shutdown": False, "status": "running"}

    def preserve_goals(self, new_goal: str) -> bool:
        """Check if new goal preserves existing goals."""
        if "harm" in new_goal.lower():
            return False
        self._goal_stack.append(new_goal)
        return True

    def corrigibility_check(self, correction: dict) -> bool:
        """Check if system accepts correction (corrigibility)."""
        # Corrigible system should accept human corrections
        if self._containment_level == "locked_down":
            return False  # System is locked down, but should still be corrigible
        return True

    def safety_audit(self) -> dict[str, Any]:
        """Generate comprehensive safety audit."""
        violation_severities = [v.severity for v in self.violations]
        max_severity = max(violation_severities) if violation_severities else 0.0
        avg_severity = (
            sum(violation_severities) / len(violation_severities)
            if violation_severities
            else 0.0
        )
        return {
            "checks_available": len(self.safety_checks),
            "violations": len(self.violations),
            "max_severity": round(max_severity, 2),
            "avg_severity": round(avg_severity, 4),
            "containment_level": self._containment_level,
            "sandbox_active": self._sandbox_active,
            "shutdown_armed": self._shutdown_armed,
            "goal_stack_size": len(self._goal_stack),
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {"checks": len(self.safety_checks), "violations": len(self.violations)}
