"""AIOS v22.3 Goal Manager foundation.

Provides a minimal goal lifecycle abstraction for cognitive workflows.
"""

class GoalManager:
    def __init__(self):
        self.goals = []

    def create_goal(self, goal):
        self.goals.append(goal)
        return goal

    def list_goals(self):
        return list(self.goals)
