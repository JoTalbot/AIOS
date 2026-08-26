import asyncio

import pytest

from runtime.tool_executor import ToolExecutor
from runtime.tool_protocol import ToolCall
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox


async def slow():
    await asyncio.sleep(0.05)
    return "done"


async def fail():
    raise RuntimeError("broken")


@pytest.mark.asyncio
async def test_tool_executor_returns_typed_failure_on_error():
    registry = ToolRegistry()
    registry.register("fail", fail)
    result = await ToolExecutor(ToolSandbox(registry)).execute(
        ToolCall("fail", call_id="c1"),
        __import__("runtime.tool_sandbox", fromlist=["ToolExecutionContext"]).ToolExecutionContext("agent-1"),
    )
    assert result.ok is False
    assert result.call_id == "c1"


@pytest.mark.asyncio
async def test_tool_executor_enforces_timeout():
    registry = ToolRegistry()
    registry.register("slow", slow)
    result = await ToolExecutor(ToolSandbox(registry)).execute(
        ToolCall("slow", call_id="c2", timeout=0.001),
        __import__("runtime.tool_sandbox", fromlist=["ToolExecutionContext"]).ToolExecutionContext("agent-1"),
    )
    assert result.ok is False
    assert "Timeout" in (result.error or "") or "timeout" in (result.error or "").lower()
