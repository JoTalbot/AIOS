class CapabilityMatcher:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, capabilities):
        self.agents[agent_id] = capabilities

    def match(self, required):
        return [
            agent_id for agent_id, caps in self.agents.items()
            if all(item in caps for item in required)
        ]
