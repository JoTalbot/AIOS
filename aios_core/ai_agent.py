"""AI Agent Abstraction for AIOS"""

from typing import Any, Dict, Callable
from dataclasses import dataclass, field


@dataclass
class AIAgent:
    """Represents an autonomous AI agent."""

    id: str
    name: str
    capabilities: list = field(default_factory=list)
    autonomy_level: int = 2
    memory: Dict = field(default_factory=dict)

    def act(self, goal: str, context: Dict = None) -> Dict:
        """Execute an action toward a goal."""
        return {
            "agent_id": self.id,
            "goal": goal,
            "status": "executed",
            "result": f"Agent {self.name} completed: {goal}",
        }

    def learn(self, experience: Dict):
        self.memory[str(len(self.memory))] = experience

    def stats(self) -> dict:
        return {
            "id": self.id,
            "autonomy": self.autonomy_level,
            "experiences": len(self.memory),
        }
