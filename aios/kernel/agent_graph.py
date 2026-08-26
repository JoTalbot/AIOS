"""AIOS v20.6 agent graph primitives."""

from dataclasses import dataclass, field


@dataclass
class AgentGraph:
    agents: dict[str, object] = field(default_factory=dict)
    edges: dict[str, list[str]] = field(default_factory=dict)

    def add_agent(self, agent_id: str, agent: object):
        self.agents[agent_id] = agent
        self.edges.setdefault(agent_id, [])

    def connect(self, source: str, target: str):
        self.edges.setdefault(source, []).append(target)

    def neighbors(self, agent_id: str):
        return self.edges.get(agent_id, [])
