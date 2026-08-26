"""AIOS v20 Agent Registry."""


class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, metadata):
        self.agents[agent_id] = metadata

    def get(self, agent_id):
        return self.agents.get(agent_id)

    def list_active(self):
        return list(self.agents.keys())
