class GoalReasoningEngine:
    def __init__(self):
        self.goals = []

    def add_goal(self, goal, priority=0):
        self.goals.append({"goal": goal, "priority": priority})

    def prioritize(self):
        return sorted(self.goals, key=lambda item: item["priority"], reverse=True)
