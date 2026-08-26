class Planner:
    def __init__(self, memory=None):
        self.memory = memory

    async def create_plan(self, goal):
        return [
            {
                "step": 1,
                "action": "analyze",
                "goal": goal
            },
            {
                "step": 2,
                "action": "execute",
                "goal": goal
            }
        ]
