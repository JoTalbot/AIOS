"""AIOS v20 policy engine foundation."""

from dataclasses import dataclass


@dataclass
class Policy:
    name: str
    enabled: bool = True


class PolicyEngine:
    def __init__(self):
        self.policies: dict[str, Policy] = {}

    def register(self, policy: Policy) -> None:
        self.policies[policy.name] = policy

    def allowed(self, name: str) -> bool:
        policy = self.policies.get(name)
        return policy.enabled if policy else False
