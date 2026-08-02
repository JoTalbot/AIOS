class AgentManager:
    def __init__(self, registry):
        self.registry = registry

    def add_agent(self, agent):
        self.registry.register(agent)

    def status(self):
        return {
            "agents": self.registry.list_agents()
        }
