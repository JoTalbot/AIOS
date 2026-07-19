"""
AIOS Agent Identity Layer v2.1.1

Defines agent identity and responsibility boundaries.
"""


class AgentIdentity:
    def __init__(self, agent_id: str, role: str, scope: list):
        self.agent_id = agent_id
        self.role = role
        self.scope = scope

    def can_access(self, resource: str) -> bool:
        return resource in self.scope

    def describe(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "scope": self.scope,
        }
