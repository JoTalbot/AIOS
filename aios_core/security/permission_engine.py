"""AIOS Permission Engine.

Controls whether an agent is allowed to execute an action.
"""

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class PermissionPolicy:
    agent_id: str
    allowed_actions: Set[str] = field(default_factory=set)

    def allows(self, action: str) -> bool:
        return action in self.allowed_actions or "*" in self.allowed_actions


class PermissionEngine:
    def __init__(self):
        self.policies: Dict[str, PermissionPolicy] = {}

    def register_policy(self, policy: PermissionPolicy):
        self.policies[policy.agent_id] = policy

    def check(self, agent_id: str, action: str) -> bool:
        policy = self.policies.get(agent_id)
        if not policy:
            return False
        return policy.allows(action)
