class AgentMarketplace:
    """Agent capability marketplace foundation."""

    def __init__(self):
        self.capabilities = {}

    def publish(self, agent, capability):
        self.capabilities.setdefault(agent, []).append(capability)

    def list(self):
        return self.capabilities
