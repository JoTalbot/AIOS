"""Explainable AI (XAI) for AIOS"""

from typing import Dict, List


class ExplainableAI:
    """Provides explanations for AI decisions."""

    def __init__(self):
        self.explanations: Dict[str, List[str]] = {}

    def explain(self, decision_id: str, factors: List[str]) -> str:
        explanation = f"Decision {decision_id} was made because: " + ", ".join(factors)
        self.explanations[decision_id] = factors
        return explanation

    def get_explanation(self, decision_id: str) -> str:
        factors = self.explanations.get(decision_id, [])
        return " + ".join(factors) if factors else "No explanation available"

    def stats(self) -> dict:
        return {"explained_decisions": len(self.explanations)}