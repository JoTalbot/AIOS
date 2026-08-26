"""AIOS v27.1 Autonomous Agent Society"""

class AgentSociety:
    def __init__(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)
