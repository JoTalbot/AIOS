"""Agent reputation model for adaptive routing."""

from dataclasses import dataclass


@dataclass
class AgentReputation:
    agent_id: str
    score: float = 0.5

    def reward(self, value: float = 0.05):
        self.score = min(1.0, self.score + value)
        return self.score

    def penalize(self, value: float = 0.05):
        self.score = max(0.0, self.score - value)
        return self.score
