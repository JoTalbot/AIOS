class PlannerAgent:
    def __init__(self, agent_runtime):
        self.runtime = agent_runtime

    def create_plan(self, goal):
        return {
            "goal": goal,
            "tasks": []
        }
