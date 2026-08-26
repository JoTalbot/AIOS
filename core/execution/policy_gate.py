"""Execution policy gate.

Provides a lightweight authorization boundary before runtime execution.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""


class ExecutionPolicy(Protocol):
    def evaluate(self, context: Any) -> PolicyDecision:
        ...


class PolicyGate:
    """Checks execution permission before entering runtime."""

    def __init__(self, policy: ExecutionPolicy | None = None):
        self.policy = policy

    def check(self, context: Any) -> PolicyDecision:
        if self.policy is None:
            return PolicyDecision(allowed=True, reason="no policy configured")
        return self.policy.evaluate(context)
