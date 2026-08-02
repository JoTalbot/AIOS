class AgentRegistry:
    """Universal agent registry foundation."""

    def __init__(self):
        self.agents = {}

    def register(self, name, agent):
        self.agents[name] = agent

    def get(self, name):
        return self.agents.get(name)
