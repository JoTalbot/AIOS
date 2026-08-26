"""Belief management layer for cognitive reasoning."""

from dataclasses import dataclass, field


@dataclass
class BeliefSystem:
    beliefs: dict[str, float] = field(default_factory=dict)

    def update(self, statement: str, confidence: float):
        self.beliefs[statement] = confidence

    def confidence(self, statement: str) -> float:
        return self.beliefs.get(statement, 0.0)
