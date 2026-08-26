class GoalScheduler:
    """Schedules cognitive goals by priority."""

    def __init__(self):
        self.goals = []

    def add_goal(self, goal):
        self.goals.append(goal)

    def next_goal(self):
        if not self.goals:
            return None
        return sorted(self.goals, key=lambda g: getattr(g, "priority", 0), reverse=True)[0]
