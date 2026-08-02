class TasksAPI:
    """Task submission API foundation."""

    def __init__(self, runtime=None):
        self.runtime = runtime

    async def run(self, agent, task):
        if not self.runtime:
            return {"status": "no_runtime"}
        return await self.runtime.execute(agent, task)
