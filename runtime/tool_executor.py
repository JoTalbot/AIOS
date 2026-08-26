"""Timeout/cancellation aware execution of typed tool calls."""

import asyncio

from .tool_protocol import ToolCall, ToolResult
from .tool_sandbox import ToolExecutionContext, ToolSandbox


class ToolExecutor:
    def __init__(self, sandbox: ToolSandbox):
        self.sandbox = sandbox

    async def execute(self, call: ToolCall, context: ToolExecutionContext) -> ToolResult:
        try:
            operation = self.sandbox.execute(call.tool, context, **call.arguments)
            if call.timeout is not None:
                value = await asyncio.wait_for(operation, timeout=call.timeout)
            else:
                value = await operation
            return ToolResult.success(call, value)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return ToolResult.failure(call, exc)
