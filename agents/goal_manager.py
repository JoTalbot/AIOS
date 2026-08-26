class GoalManager:
    def __init__(self):
        self.goals = []

    def add_goal(self, goal):
        self.goals.append({"goal": goal, "status": "pending"})

    def active_goals(self):
        return [g for g in self.goals if g["status"] == "pending"]
