"""Conservative sandbox boundary for policy-approved agent handlers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .contracts import AgentResult, AgentStatus, AgentTask


@dataclass(frozen=True)
class SandboxPolicy:
    allowed_permissions: tuple[str, ...] = ()
    max_budget: int | None = None
    network: bool = False
    filesystem: bool = False


class SandboxExecutor:
    """Validate sandbox constraints before delegating to an agent handler.

    This is a policy boundary, not an OS-level isolation mechanism. Real process/container
    isolation must be supplied by a trusted runtime backend before untrusted code is run.
    """

    def __init__(self, handler: Callable[[AgentTask], AgentResult], policy: SandboxPolicy) -> None:
        self.handler = handler
        self.policy = policy

    def validate(self, task: AgentTask) -> tuple[bool, str]:
        requested = set(task.permissions)
        allowed = set(self.policy.allowed_permissions)
        if not requested.issubset(allowed):
            return False, "requested permission is outside sandbox policy"
        if self.policy.max_budget is not None and task.budget is not None and task.budget > self.policy.max_budget:
            return False, "task budget exceeds sandbox limit"
        if "network" in requested and not self.policy.network:
            return False, "network access is disabled in sandbox"
        if "filesystem.write" in requested and not self.policy.filesystem:
            return False, "filesystem write access is disabled in sandbox"
        return True, "sandbox policy accepted"

    def execute(self, task: AgentTask) -> AgentResult:
        allowed, reason = self.validate(task)
        if not allowed:
            return AgentResult(task_id=task.task_id, status=AgentStatus.BLOCKED, errors=(reason,), verdict="SANDBOX_BLOCKED")
        return self.handler(task)
