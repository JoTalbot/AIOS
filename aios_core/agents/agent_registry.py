from typing import Dict

class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, object] = {}

    def register(self, agent):
        self.agents[agent.id] = agent

    def get(self, agent_id):
        return self.agents.get(agent_id)

    def list_agents(self):
        return list(self.agents.values())
