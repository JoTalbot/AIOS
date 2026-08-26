"""AIOS Task Router

Routes tasks to agents based on capabilities.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class RoutedTask:
    task_id: str
    agent_id: str
    payload: dict[str, Any]


class TaskRouter:
    def __init__(self, registry):
        self.registry = registry

    def route(self, task: dict[str, Any]) -> RoutedTask:
        capability = task.get("capability")
        agent = self.registry.find_by_capability(capability)
        if agent is None:
            raise RuntimeError(f"No agent available for capability: {capability}")

        return RoutedTask(
            task_id=task.get("id", "unknown"),
            agent_id=agent.id,
            payload=task,
        )
