class AgentCoordinator:
    def __init__(self, manager):
        self.manager = manager

    async def dispatch(self, agent_name, task):
        agent = self.manager.registry.get(agent_name)
        if agent is None:
            raise ValueError(f"Unknown agent: {agent_name}")
        return await agent.execute(task)
