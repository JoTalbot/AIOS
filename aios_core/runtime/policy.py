"""Policy and permission checks for AIOS agent execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import AgentTask


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    SANDBOX = "sandbox"
    APPROVAL_REQUIRED = "approval_required"


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str
    permission: str | None = None


class PolicyEngine:
    """Fail-closed policy evaluator based on explicit task permissions."""

    def __init__(self, *, approval_permissions: tuple[str, ...] = (), sandbox_permissions: tuple[str, ...] = ()) -> None:
        self.approval_permissions = frozenset(approval_permissions)
        self.sandbox_permissions = frozenset(sandbox_permissions)

    def check(self, task: AgentTask, permission: str) -> PolicyResult:
        permissions = frozenset(task.permissions)
        if permission not in permissions:
            return PolicyResult(PolicyDecision.DENY, "permission not granted", permission)
        if permission in self.approval_permissions:
            return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "explicit approval required", permission)
        if permission in self.sandbox_permissions:
            return PolicyResult(PolicyDecision.SANDBOX, "operation must run in sandbox", permission)
        return PolicyResult(PolicyDecision.ALLOW, "permission granted", permission)
