"""AIOS v21 goal management foundation."""

from dataclasses import dataclass


@dataclass
class Goal:
    name: str
    priority: float = 0.0


class GoalEngine:
    def __init__(self):
        self.goals = []

    def add_goal(self, goal: Goal):
        self.goals.append(goal)

    def next_goal(self):
        return max(self.goals, key=lambda g: g.priority, default=None)
