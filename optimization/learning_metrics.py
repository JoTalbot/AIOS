from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentMetric:
    agent_id: str
    rewards: List[float] = field(default_factory=list)

    @property
    def average_reward(self) -> float:
        if not self.rewards:
            return 0.0
        return sum(self.rewards) / len(self.rewards)


class LearningMetrics:
    """Tracks learning performance across agents."""

    def __init__(self):
        self.metrics: Dict[str, AgentMetric] = {}

    def register_agent(self, agent_id: str):
        if agent_id not in self.metrics:
            self.metrics[agent_id] = AgentMetric(agent_id)

    def record_reward(self, agent_id: str, reward: float):
        self.register_agent(agent_id)
        self.metrics[agent_id].rewards.append(reward)

    def get_agent_score(self, agent_id: str) -> float:
        metric = self.metrics.get(agent_id)
        return metric.average_reward if metric else 0.0
