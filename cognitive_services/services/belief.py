from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BeliefService:
    """Tracks confidence-weighted internal beliefs."""

    beliefs: Dict[str, float] = field(default_factory=dict)

    def health(self) -> bool:
        return True

    def update(self, key: str, confidence: float) -> None:
        self.beliefs[key] = confidence

    def confidence(self, key: str) -> float:
        return self.beliefs.get(key, 0.0)
