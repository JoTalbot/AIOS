"""Multi-Agent Swarm System for AIOS"""

from typing import Dict, List

from .agent_architecture import AdvancedAgent

__all__ = ["AgentSwarm"]


class AgentSwarm:
    """Swarm of collaborative agents."""

    def __init__(self, name: str):
        self.name = name
        self.agents: List[AdvancedAgent] = []
        self.shared_memory: Dict = {}
        self.consensus: Dict = {}

    def add_agent(self, agent: AdvancedAgent) -> None:
        self.agents.append(agent)

    def broadcast(self, message: Dict) -> None:
        for agent in self.agents:
            agent.memory.short_term.append(message)

    def collective_decision(self, topic: str) -> Dict:
        # Simple majority vote simulation
        return {"decision": "approved", "topic": topic, "votes": len(self.agents)}

    def stats(self) -> dict:
        return {"agents": len(self.agents), "shared_memory": len(self.shared_memory)}
