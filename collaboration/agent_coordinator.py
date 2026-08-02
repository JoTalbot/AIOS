class AgentCoordinator:
    """AIOS agent coordination foundation."""

    def __init__(self):
        self.agents = []

    def add(self, agent):
        self.agents.append(agent)

    def list(self):
        return self.agents
