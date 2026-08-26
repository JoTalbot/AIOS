"""Policy-aware execution boundary.

Combines admission control with execution entry point.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PolicyExecutionResult:
    allowed: bool
    reason: str | None = None


class PolicyAwareBoundary:
    def __init__(self, policy_gate: Any, boundary: Any, audit: Any = None):
        self.policy_gate = policy_gate
        self.boundary = boundary
        self.audit = audit

    async def execute(self, context: Any):
        decision = self.policy_gate.check(context)

        if not decision.allowed:
            if self.audit:
                self.audit.record({
                    "event": "policy.denied",
                    "context": context,
                })
            return PolicyExecutionResult(False, decision.reason)

        if self.audit:
            self.audit.record({
                "event": "policy.allowed",
                "context": context,
            })

        return await self.boundary.execute(context)
