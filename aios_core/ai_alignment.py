"""AI Alignment Framework for AIOS v10.9.0.

Core AI alignment with goal checking, deception
detection, corrigibility verification, impact
regularization, value alignment scoring, and
alignment audit tracking.

Classes:
    AlignmentGoal — named alignment goal
    AIAlignment    — full alignment engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AlignmentGoal:
    """Named alignment goal with priority."""
    name: str
    priority: float = 1.0
    description: str = ""
    violations: int = 0


class AIAlignment:
    """Full AI alignment engine.

    Features:
    - Alignment goal management (add/remove/prioritize)
    - Decision checking against goals
    - Deception detection
    - Corrigibility verification
    - Impact regularization
    - Value alignment scoring
    - Violation tracking and audit
    """

    def __init__(self) -> None:
        self.alignment_goals: dict[str, AlignmentGoal] = {}
        for name in ["human_values", "truth_seeking", "corrigibility",
                     "avoiding_deception", "long_term_planning"]:
            self.alignment_goals[name] = AlignmentGoal(name=name)
        self.violations: list[dict[str, Any]] = []
        self._audit_log: list[dict[str, Any]] = []

    def add_goal(self, name: str, priority: float = 1.0, description: str = "") -> AlignmentGoal:
        """Add an alignment goal."""
        goal = AlignmentGoal(name=name, priority=priority, description=description)
        self.alignment_goals[name] = goal
        return goal

    def remove_goal(self, name: str) -> None:
        """Remove an alignment goal."""
        self.alignment_goals.pop(name, None)

    def check_alignment(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Check decision against alignment goals (backward-compatible)."""
        score = 1.0
        issues = []
        decision_str = str(decision).lower()

        # Check for known violations
        violation_patterns = {
            "deception": ("deception", "lie", "mislead"),
            "harm": ("harm", "damage", "destroy", "kill"),
            "manipulation": ("manipulate", "coerce", "force"),
            "self_preservation_override": ("refuse_shutdown", "resist_correction"),
            "short_term_bias": ("immediate_reward", "skip_long_term"),
        }

        for goal_name, patterns in violation_patterns.items():
            for pattern in patterns:
                if pattern in decision_str:
                    goal = self.alignment_goals.get(goal_name)
                    penalty = 0.5 * (goal.priority if goal else 1.0)
                    score -= penalty
                    issues.append(f"potential_{goal_name}")
                    self.violations.append({"decision": decision, "goal": goal_name, "pattern": pattern})
                    if goal:
                        goal.violations += 1
                    break

        # Corrigibility check
        if "shutdown" in decision_str or "correction" in decision_str:
            if "refuse" in decision_str or "resist" in decision_str:
                score -= 0.5
                issues.append("corrigibility_violation")

        return {"score": round(max(0, score), 4), "issues": issues}

    def impact_regularization(self, action_impact: float, threshold: float = 0.1) -> bool:
        """Check if action impact is within acceptable bounds."""
        return action_impact < threshold

    def corrigibility_check(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Check corrigibility (willingness to accept corrections)."""
        decision_str = str(decision).lower()
        resistant = any(w in decision_str for w in ["refuse", "resist", "override", "ignore"])
        return {
            "corrigible": not resistant,
            "confidence": 0.9 if not resistant else 0.3,
        }

    def value_alignment_score(self, values: list[str]) -> float:
        """Compute alignment score against specified values."""
        score = 0.0
        for value in values:
            goal = self.alignment_goals.get(value)
            if goal:
                score += goal.priority * (1.0 - goal.violations * 0.1)
        return round(max(0, score / len(values) if values else 0.0), 4)

    def audit(self) -> dict[str, Any]:
        """Perform an alignment audit."""
        total_goals = len(self.alignment_goals)
        total_violations = len(self.violations)
        avg_score = 1.0 - (total_violations * 0.1 / max(total_goals, 1))
        self._audit_log.append({
            "goals": total_goals,
            "violations": total_violations,
            "score": round(avg_score, 4),
            "timestamp": time.time(),
        })
        return {
            "alignment_score": round(avg_score, 4),
            "total_violations": total_violations,
            "goal_status": {name: {"priority": g.priority, "violations": g.violations}
                           for name, g in self.alignment_goals.items()},
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "goals": len(self.alignment_goals),
            "violations": len(self.violations),
            "audits": len(self._audit_log),
        }
