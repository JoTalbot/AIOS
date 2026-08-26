"""AIOS execution pipeline."""


class ExecutionPipeline:
    def __init__(self, runtime):
        self.runtime = runtime

    async def execute(self, task):
        agent = await self.runtime.resolve_agent(task)
        return await agent.execute(task)
