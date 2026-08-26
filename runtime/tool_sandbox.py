"""Minimal execution boundary for AIOS tools.

The sandbox intentionally starts with policy controls rather than pretending
that an in-process Python call is a security sandbox. OS isolation can be
plugged in later without changing the registry contract.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .tool_registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionContext:
    agent_id: str
    permissions: frozenset[str] = frozenset()


class ToolSandbox:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, tool_name: str, context: ToolExecutionContext, **kwargs) -> Any:
        if not context.agent_id:
            raise PermissionError("agent identity is required")
        return await self.registry.execute(
            tool_name,
            granted_permissions=context.permissions,
            **kwargs,
        )
