"""Agent discovery layer for AIOS.

Provides foundation for automatic agent registration and lookup.
"""

class AgentDiscovery:
    def __init__(self):
        self.agents = {}

    def register(self, agent):
        self.agents[agent.name] = agent

    def get(self, name):
        return self.agents.get(name)
