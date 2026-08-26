"""AIOS agent executor foundation."""


class AgentExecutor:
    """Executes agent tasks inside runtime."""

    def __init__(self, agent):
        self.agent = agent

    async def run(self, task):
        return await self.agent.execute(task)
