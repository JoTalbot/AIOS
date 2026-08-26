"""Agent discovery primitives for AIOS Federation."""

from typing import Dict, List


class AgentDiscovery:
    def __init__(self):
        self.agents: Dict[str, Dict] = {}

    def announce(self, agent_id: str, capabilities: List[str]):
        self.agents[agent_id] = {"capabilities": capabilities}

    def find_by_capability(self, capability: str):
        return [
            agent_id
            for agent_id, data in self.agents.items()
            if capability in data["capabilities"]
        ]
