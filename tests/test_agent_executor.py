import pytest

from kernel.scheduler import Scheduler
from runtime.agent_executor import AgentExecutor
from runtime.execution_audit import ExecutionAudit
from runtime.tool_registry import ToolRegistry
from runtime.tool_sandbox import ToolSandbox
from runtime.vnext_orchestrator import VNextOrchestrator


async def add(a, b):
    return a + b


class Planner:
    async def create_plan(self, goal):
        return [{"tool": "add", "arguments": {"a": 2, "b": 3}}]


class Agent:
    id = "agent-1"


@pytest.mark.asyncio
async def test_orchestrator_executes_plan_through_tool_boundary():
    registry = ToolRegistry()
    registry.register("add", add, permissions={"compute"})
    audit = ExecutionAudit()
    sandbox = ToolSandbox(registry, audit)
    executor = AgentExecutor(sandbox)
    orchestrator = VNextOrchestrator(
        planner=Planner(),
        scheduler=Scheduler(),
        agent=Agent(),
        executor=executor,
    )

    result = await orchestrator.run("calculate", "task-1", {"permissions": ["compute"]})

    assert result.status == "completed"
    assert result.result == [5]
    assert [event.event for event in audit.snapshot()] == [
        "tool.execution.started",
        "tool.execution.completed",
    ]
