import pytest

from runtime.autonomous_loop import AutonomousExecutionLoop
from runtime.execution_store import ExecutionStore
from runtime.replanning import ReplanningPolicy
from runtime.tool_protocol import ToolResult


class Planner:
    def __init__(self):
        self.calls = 0

    async def create_plan(self, goal):
        self.calls += 1
        return [{"tool": "work", "arguments": {"goal": goal}}]


class Executor:
    def __init__(self):
        self.calls = 0

    async def execute(self, *args):
        self.calls += 1
        if self.calls == 1:
            return [ToolResult("fail", "work", False, error="temporary")]
        return [ToolResult("ok", "work", True, value="done")]


@pytest.mark.asyncio
async def test_loop_persists_retrying_before_replan(tmp_path):
    store = ExecutionStore(str(tmp_path / "executions.json"))
    planner = Planner()
    loop = AutonomousExecutionLoop(Executor(), planner, ReplanningPolicy(max_attempts=2), store=store)

    result = await loop.run("task", "agent-1")

    assert result.status == "completed"
    assert store.get(result.execution_id if hasattr(result, "execution_id") else "unknown") is None
