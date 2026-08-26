"""Policy-aware execution boundary for AIOS tools."""

from dataclasses import dataclass
from typing import Any

from .execution_audit import ExecutionAudit
from .tool_registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionContext:
    agent_id: str
    permissions: frozenset[str] = frozenset()


class ToolSandbox:
    def __init__(self, registry: ToolRegistry, audit: ExecutionAudit | None = None):
        self.registry = registry
        self.audit = audit or ExecutionAudit()

    async def execute(self, tool_name: str, context: ToolExecutionContext, **kwargs) -> Any:
        if not context.agent_id:
            raise PermissionError("agent identity is required")
        self.audit.record("tool.execution.started", context.agent_id, tool_name)
        try:
            result = await self.registry.execute(
                tool_name,
                granted_permissions=context.permissions,
                **kwargs,
            )
            self.audit.record("tool.execution.completed", context.agent_id, tool_name)
            return result
        except Exception as exc:
            self.audit.record("tool.execution.failed", context.agent_id, tool_name, "error", error=str(exc))
            raise
