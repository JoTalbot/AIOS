class GoalManager:
    """Autonomous goal lifecycle foundation."""

    def __init__(self):
        self.goals = []

    def add(self, goal):
        self.goals.append(goal)

    def active(self):
        return self.goals
