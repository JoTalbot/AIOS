"""Execution adapter between scheduler tasks, agents and typed tool protocol."""

import asyncio
from typing import Any, Optional

from .tool_executor import ToolExecutor
from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext


class AgentExecutor:
    """Execute an agent plan through the typed, policy-aware tool boundary."""

    def __init__(self, tool_executor: ToolExecutor, memory: Optional[Any] = None, retries: int = 0):
        self.tool_executor = tool_executor
        self.memory = memory
        self.retries = max(0, retries)

    async def execute(self, agent: Any, plan: Any, context: Optional[dict] = None) -> Any:
        context = dict(context or {})
        agent_id = str(getattr(agent, "id", None) or agent)
        permissions = frozenset(context.get("permissions", ()))
        results = []

        for index, step in enumerate(plan or ()):
            if not isinstance(step, dict):
                results.append(step)
                continue
            tool = step.get("tool") or step.get("action")
            if not tool:
                results.append(step)
                continue

            call = ToolCall(
                tool=tool,
                arguments=dict(step.get("arguments") or step.get("kwargs") or {}),
                call_id=str(step.get("call_id") or f"{agent_id}:{index}"),
                timeout=step.get("timeout"),
            )
            result = await self._execute_with_retry(call, agent_id, permissions)
            results.append(result)
            if self.memory and hasattr(self.memory, "remember"):
                self.memory.remember({
                    "agent_id": agent_id,
                    "tool": tool,
                    "call_id": call.call_id,
                    "ok": result.ok,
                    "result": result.value,
                    "error": result.error,
                })

        return results

    async def _execute_with_retry(self, call: ToolCall, agent_id: str, permissions: frozenset[str]) -> ToolResult:
        context = ToolExecutionContext(agent_id=agent_id, permissions=permissions)
        result = await self.tool_executor.execute(call, context)
        attempts = 0
        while not result.ok and attempts < self.retries:
            attempts += 1
            await asyncio.sleep(min(0.25 * (2 ** (attempts - 1)), 2.0))
            result = await self.tool_executor.execute(call, context)
        return result
