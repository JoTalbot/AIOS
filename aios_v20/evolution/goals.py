"""AIOS Goal Manager foundation."""

from dataclasses import dataclass


@dataclass
class Goal:
    id: str
    description: str
    status: str = "created"


class GoalManager:
    def create(self, goal_id: str, description: str) -> Goal:
        return Goal(goal_id, description)
