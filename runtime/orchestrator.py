class Orchestrator:
    def __init__(self, runtime=None):
        self.runtime = runtime
        self.components = {}

    def register(self, name, component):
        self.components[name] = component

    async def execute_goal(self, goal):
        if self.runtime:
            return await self.runtime.run(goal)

        return {
            "goal": goal,
            "status": "queued"
        }
