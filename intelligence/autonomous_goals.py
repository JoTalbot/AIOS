class AutonomousGoals:
    """Autonomous goal management foundation."""

    def __init__(self):
        self.goals = []

    def add(self, goal):
        self.goals.append(goal)

    def list(self):
        return self.goals
