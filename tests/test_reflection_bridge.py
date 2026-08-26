import pytest

from runtime.reflection_result import ToolReflectionBridge
from runtime.replanning import ReflectionReplanner, ReplanningPolicy
from runtime.tool_protocol import ToolResult


class Planner:
    async def create_plan(self, goal):
        return [{"tool": "recovery", "arguments": {"goal": goal}}]


class Memory:
    def __init__(self):
        self.items = []

    def remember(self, item, permanent=False):
        self.items.append(item)


@pytest.mark.asyncio
async def test_failed_tool_result_triggers_replan():
    memory = Memory()
    replanner = ReflectionReplanner(Planner(), memory, ReplanningPolicy(max_attempts=2))
    bridge = ToolReflectionBridge(replanner)

    failed = ToolResult.failure(
        __import__("runtime.tool_protocol", fromlist=["ToolCall"]).ToolCall("broken", call_id="c1"),
        RuntimeError("temporary failure"),
    )
    outcome = await bridge.evaluate("goal", 0, failed)

    assert outcome.ok is False
    assert outcome.decision.retry is True
    assert outcome.plan
    assert memory.items


@pytest.mark.asyncio
async def test_successful_tool_result_does_not_replan():
    replanner = ReflectionReplanner(Planner())
    bridge = ToolReflectionBridge(replanner)
    success = ToolResult.success(
        __import__("runtime.tool_protocol", fromlist=["ToolCall"]).ToolCall("ok"),
        42,
    )
    outcome = await bridge.evaluate("goal", 0, success)
    assert outcome.ok is True
    assert outcome.plan is None
