class AgentCoordinator:
    """Coordinates task execution between AIOS agents."""

    def __init__(self, registry=None, bus=None):
        self.registry = registry
        self.bus = bus

    async def dispatch(self, agent_name, task):
        agent = self.registry.get(agent_name) if self.registry else None
        if not agent:
            return {"status": "agent_not_found", "agent": agent_name}

        return await agent.execute(task)
