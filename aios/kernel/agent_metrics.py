"""Agent performance metrics for AIOS v20.7."""

from dataclasses import dataclass
from time import time


@dataclass
class AgentMetric:
    agent_id: str
    success_rate: float = 0.0
    tasks_completed: int = 0
    updated_at: float = 0.0


class AgentMetrics:
    def __init__(self):
        self.metrics = {}

    def update(self, agent_id: str, success: bool):
        metric = self.metrics.get(agent_id, AgentMetric(agent_id))
        metric.tasks_completed += 1
        metric.success_rate = ((metric.success_rate * (metric.tasks_completed - 1)) + int(success)) / metric.tasks_completed
        metric.updated_at = time()
        self.metrics[agent_id] = metric
        return metric

    def get(self, agent_id: str):
        return self.metrics.get(agent_id)
