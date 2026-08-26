"""Execution adapter between scheduler tasks, agents and tool sandbox."""

from typing import Any, Optional

from .tool_sandbox import ToolExecutionContext, ToolSandbox


class AgentExecutor:
    """Execute an agent plan through the policy-aware tool boundary."""

    def __init__(self, sandbox: ToolSandbox, memory: Optional[Any] = None):
        self.sandbox = sandbox
        self.memory = memory

    async def execute(self, agent: Any, plan: Any, context: Optional[dict] = None) -> Any:
        context = dict(context or {})
        agent_id = str(getattr(agent, "id", None) or agent)
        permissions = frozenset(context.get("permissions", ()))
        results = []

        for step in plan or ():
            if not isinstance(step, dict):
                results.append(step)
                continue
            tool = step.get("tool") or step.get("action")
            if not tool:
                results.append(step)
                continue
            kwargs = dict(step.get("arguments") or step.get("kwargs") or {})
            result = await self.sandbox.execute(
                tool,
                ToolExecutionContext(agent_id=agent_id, permissions=permissions),
                **kwargs,
            )
            results.append(result)
            if self.memory and hasattr(self.memory, "remember"):
                self.memory.remember({"agent_id": agent_id, "tool": tool, "result": result})

        return results
