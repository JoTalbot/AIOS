"""Memory optimization loop for AIOS learning cycle."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class MemoryOptimizationResult:
    key: str
    score: float
    updated: bool


class MemoryOptimizationLoop:
    """Connect memory experience quality with optimization feedback."""

    def __init__(self):
        self.scores: Dict[str, float] = {}

    def update(self, key: str, reward: float) -> MemoryOptimizationResult:
        self.scores[key] = max(0.0, min(1.0, reward))
        return MemoryOptimizationResult(
            key=key,
            score=self.scores[key],
            updated=True,
        )

    def get_score(self, key: str) -> float:
        return self.scores.get(key, 0.0)
