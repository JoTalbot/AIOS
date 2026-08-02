class AgentRegistry:
    """Autonomous agent registry foundation."""

    def __init__(self):
        self.agents = {}

    def register(self, agent_id, data):
        self.agents[agent_id] = data

    def get(self, agent_id):
        return self.agents.get(agent_id)
