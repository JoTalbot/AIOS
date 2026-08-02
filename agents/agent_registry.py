class AgentRegistry:
    """AIOS agent registry foundation."""

    def __init__(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)

    def list_agents(self):
        return self.agents
