"""Recovery experience memory for AIOS adaptive decisions."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class RecoveryExperience:
    failure_type: str
    action: str
    success: bool
    reward: float = 0.0


class RecoveryMemory:
    """Stores recovery outcomes for future policy improvements."""

    def __init__(self):
        self.experiences: List[RecoveryExperience] = []

    def remember(self, experience: RecoveryExperience) -> None:
        self.experiences.append(experience)

    def find_successful(self, failure_type: str):
        return [
            item
            for item in self.experiences
            if item.failure_type == failure_type and item.success
        ]

    def score_action(self, failure_type: str, action: str) -> float:
        matches = [
            item.reward
            for item in self.experiences
            if item.failure_type == failure_type and item.action == action
        ]

        return sum(matches) / len(matches) if matches else 0.0
