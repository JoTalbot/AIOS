"""AIOS Agent Registry foundation."""

from dataclasses import dataclass


@dataclass
class Agent:
    agent_id: str
    role: str
    status: str = "idle"


class AgentRegistry:

    def __init__(self):
        self.agents = {}

    def register(self, agent: Agent):
        self.agents[agent.agent_id] = agent

    def get(self, agent_id: str):
        return self.agents.get(agent_id)

    def available(self):
        return [
            agent
            for agent in self.agents.values()
            if agent.status == "idle"
        ]
