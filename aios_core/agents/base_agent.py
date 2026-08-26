"""AIOS Base Agent Core.

Foundation class for all AIOS agents.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseAgent:
    agent_id: str
    name: str
    skills: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    status: str = "created"

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        self.status = "running"
        result = {
            "agent": self.agent_id,
            "task": task,
            "status": "completed",
        }
        self.status = "completed"
        return result

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def remember(self, key: str, value: Any):
        self.memory[key] = value
