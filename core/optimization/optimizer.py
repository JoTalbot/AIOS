from dataclasses import dataclass
from typing import Dict


@dataclass
class OptimizationMetric:
    name: str
    value: float


class OptimizationLayer:
    """Analyzes execution feedback and adjusts strategy weights."""

    def __init__(self):
        self.metrics: Dict[str, float] = {}

    def update_metric(self, name: str, value: float):
        self.metrics[name] = value

    def confidence_adjustment(self, action: str) -> float:
        return self.metrics.get(action, 0.0)

    def optimize(self, policy_scores: Dict[str, float]) -> Dict[str, float]:
        return {
            action: score + self.confidence_adjustment(action)
            for action, score in policy_scores.items()
        }
