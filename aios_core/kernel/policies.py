"""AIOS v20 policy engine foundation."""

from dataclasses import dataclass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    def __init__(self):
        self.rules = {}

    def allow(self, capability: str) -> None:
        self.rules[capability] = True

    def evaluate(self, capability: str) -> PolicyDecision:
        allowed = self.rules.get(capability, False)
        return PolicyDecision(
            allowed=allowed,
            reason="allowed" if allowed else "missing_capability",
        )
