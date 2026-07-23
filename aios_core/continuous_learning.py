"""Continuous Learning Pipeline for AIOS"""

from typing import Dict, List


class ContinuousLearning:
    """Online/continuous learning system."""

    def __init__(self):
        self.knowledge_base: List[Dict] = []
        self.performance_history: List[float] = []

    def ingest_experience(self, experience: Dict) -> None:
        """Execute ingest experience."""
        self.knowledge_base.append(experience)

    def update_model(self, feedback: float) -> None:
        """Execute update model."""
        self.performance_history.append(feedback)
        # In real system: update weights

    def predict(self, input_data: Dict) -> float:
        """Execute predict."""
        # Simple average-based prediction
        if not self.performance_history:
            return 0.5
        return sum(self.performance_history[-10:]) / len(self.performance_history[-10:])

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "experiences": len(self.knowledge_base),
            "avg_performance": (
                sum(self.performance_history) / len(self.performance_history)
                if self.performance_history
                else 0
            ),
        }
