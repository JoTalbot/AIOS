"""AIOS Agent Coordination Layer v2.1.1"""

class AgentCoordinator:
    def __init__(self):
        self.agents = {}

    def register(self, agent_id, data):
        self.agents[agent_id] = data

    def status(self):
        return self.agents
