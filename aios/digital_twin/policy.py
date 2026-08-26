"""Policy guard for predictive and autonomous Digital Twin actions."""

from dataclasses import dataclass, field
from typing import Set


@dataclass
class TwinPolicy:
    allowed_actions: Set[str] = field(default_factory=set)
    require_approval: bool = True

    def allows(self, action: str) -> bool:
        return action in self.allowed_actions

    def authorize(self, action: str, approved: bool = False) -> bool:
        if not self.allows(action):
            return False
        return approved if self.require_approval else True
