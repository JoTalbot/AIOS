class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, capabilities=None):
        self.agents[agent_id] = capabilities or []

    def get(self, agent_id):
        return self.agents.get(agent_id)
