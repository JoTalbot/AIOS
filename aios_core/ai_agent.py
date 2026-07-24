"""AI Agent Abstraction for AIOS v10.9.0.

Autonomous AI agent with capabilities, autonomy levels,
memory management, action execution, learning, goal
tracking, and agent communication.

Classes:
    AgentGoal      — agent goal with progress
    AIAgent        — full autonomous AI agent
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentGoal:
    """Agent goal with progress tracking."""

    name: str
    progress: float = 0.0
    priority: float = 1.0
    completed: bool = False


@dataclass
class AIAgent:
    """Full autonomous AI agent.

    Features:
    - Capability-based action execution
    - Autonomy level management
    - Memory with experience tracking
    - Goal tracking with progress
    - Learning from experience
    - Agent communication
    """

    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    autonomy_level: int = 2  # 1=supervised, 2=semi, 3=full
    memory: dict[str, Any] = field(default_factory=dict)
    _goals: list[AgentGoal] = field(default_factory=list)
    _experience_count: int = 0

    def act(self, goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute an action toward a goal (backward-compatible)."""
        context = context or {}

        # Check autonomy level
        if self.autonomy_level == 1:
            return {
                "agent_id": self.id,
                "goal": goal,
                "status": "requires_approval",
                "result": f"Agent {self.name} needs approval for: {goal}",
            }

        # Check capability
        if goal not in self.capabilities and self.capabilities:
            return {
                "agent_id": self.id,
                "goal": goal,
                "status": "unsupported",
                "result": f"Agent {self.name} lacks capability for: {goal}",
            }

        # Execute based on autonomy level
        status = "executed" if self.autonomy_level >= 2 else "pending"
        result = f"Agent {self.name} completed: {goal}"

        # Track goal progress
        for g in self._goals:
            if g.name == goal:
                g.progress = min(1.0, g.progress + 0.3)
                if g.progress >= 1.0:
                    g.completed = True
                break

        return {"agent_id": self.id, "goal": goal, "status": status, "result": result}

    def learn(self, experience: dict[str, Any]) -> None:
        """Learn from experience (backward-compatible)."""
        self.memory[str(len(self.memory))] = experience
        self._experience_count += 1

    def add_goal(self, name: str, priority: float = 1.0) -> AgentGoal:
        """Add a goal."""
        goal = AgentGoal(name=name, priority=priority)
        self._goals.append(goal)
        return goal

    def get_goals(self) -> list[dict[str, Any]]:
        """Return all goals with progress."""
        return [
            {
                "name": g.name,
                "progress": round(g.progress, 4),
                "priority": g.priority,
                "completed": g.completed,
            }
            for g in self._goals
        ]

    def can_do(self, task: str) -> bool:
        """Check if agent can perform a task."""
        return task in self.capabilities or not self.capabilities

    def communicate(self, message: str, target: str = "") -> dict[str, Any]:
        """Send a message to another agent."""
        return {
            "from": self.id,
            "to": target,
            "message": message,
            "timestamp": time.time(),
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        return {
            "id": self.id,
            "autonomy": self.autonomy_level,
            "experiences": len(self.memory),
            "goals": len(self._goals),
            "capabilities": len(self.capabilities),
        }
