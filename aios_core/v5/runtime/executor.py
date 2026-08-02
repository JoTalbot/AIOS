class RuntimeExecutor:
    """Agent execution runtime foundation."""

    def __init__(self):
        self.running = False

    async def execute(self, agent, task):
        self.running = True
        try:
            return await agent.execute(task)
        finally:
            self.running = False
