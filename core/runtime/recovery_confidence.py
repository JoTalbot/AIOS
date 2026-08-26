"""Recovery confidence intelligence utilities for AIOS."""

from typing import Any, Dict


class RecoveryConfidenceEngine:
    """Calculates confidence levels for autonomous recovery decisions."""

    def evaluate(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        if decision.get("health") == "healthy":
            score += 40
        if decision.get("retry_available") or decision.get("retry"):
            score += 25
        if decision.get("rollback_available") or decision.get("rollback"):
            score += 35

        confidence = min(score, 100)
        return {
            "confidence": confidence,
            "risk": "low" if confidence >= 70 else "medium" if confidence >= 40 else "high",
            "decision": decision,
        }
