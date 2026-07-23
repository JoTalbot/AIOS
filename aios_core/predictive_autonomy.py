"""Predictive Autonomy Regulator for AIOS Executive Layer.

Forecasts execution failure risk based on historic model scores, step complexity,
resource demand, and agent history, dynamically scaling autonomy levels.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from .autonomy_manager import AutonomyLevel


class PredictiveAutonomyRegulator:
    """Predictive Autonomy Regulator that dynamically bounds agent execution scope."""

    def __init__(self, high_risk_threshold: float = 0.6, critical_risk_threshold: float = 0.85):
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold
        self.history: List[Dict[str, Any]] = []

    def assess_risk(
        self,
        agent_id: str,
        plan_step: Dict[str, Any],
        agent_history_stats: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate normalized failure risk score [0.0, 1.0]."""
        risk_score = 0.1  # baseline minimal risk

        # Factor 1: Plan step operational risk
        action_type = plan_step.get("action", "").lower()
        if any(
            keyword in action_type
            for keyword in ["delete", "drop", "terminate", "wipe", "force", "sudo"]
        ):
            risk_score += 0.5
        elif any(
            keyword in action_type for keyword in ["write", "modify", "deploy", "update", "exec"]
        ):
            risk_score += 0.2

        # Factor 2: Complexity and required capabilities
        complexity = plan_step.get("complexity", 1.0)
        if complexity > 5.0:
            risk_score += 0.2

        # Factor 3: Historical error rate of the agent
        if agent_history_stats:
            failure_rate = agent_history_stats.get("failure_rate", 0.0)
            risk_score += failure_rate * 0.3

        normalized_risk = min(1.0, max(0.0, risk_score))
        return normalized_risk

    def regulate_autonomy(
        self,
        agent_id: str,
        current_level: AutonomyLevel,
        plan_step: Dict[str, Any],
        agent_history_stats: Optional[Dict[str, float]] = None,
    ) -> Tuple[AutonomyLevel, str]:
        """Dynamically regulate autonomy level based on predicted task risk."""
        risk = self.assess_risk(agent_id, plan_step, agent_history_stats)
        effective_level = current_level
        reason = (
            f"Risk evaluated at {risk:.2f} — autonomy maintained at Level {current_level.value}"
        )

        if risk >= self.critical_risk_threshold:
            # Drop to Level 1 (Human-assisted approval required)
            effective_level = AutonomyLevel.LEVEL_1_ASSISTED
            reason = f"Critical Risk ({risk:.2f} >= {self.critical_risk_threshold}) — downgraded to Level 1 Assisted"

        elif (
            risk >= self.high_risk_threshold
            and current_level.value > AutonomyLevel.LEVEL_2_SUPERVISED.value
        ):
            # Clamp to Level 2 (Supervised Execution)
            effective_level = AutonomyLevel.LEVEL_2_SUPERVISED
            reason = f"High Risk ({risk:.2f} >= {self.high_risk_threshold}) — clamped to Level 2 Supervised"

        self.history.append(
            {
                "agent_id": agent_id,
                "original_level": current_level.value,
                "regulated_level": effective_level.value,
                "risk_score": round(risk, 3),
                "reason": reason,
                "timestamp": time.time(),
            }
        )

        return effective_level, reason

    def stats(self) -> Dict[str, Any]:
        """Summary of predictive regulation decisions."""
        return {
            "total_regulations": len(self.history),
            "clamped_count": sum(
                1 for h in self.history if h["regulated_level"] < h["original_level"]
            ),
            "high_risk_threshold": self.high_risk_threshold,
            "critical_risk_threshold": self.critical_risk_threshold,
        }
