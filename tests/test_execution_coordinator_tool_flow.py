import asyncio

from execution import ExecutionCoordinator, ExecutionToolAdapter
from tools.registry_auto import AutoToolRegistry


class EchoTool:
    name = "echo"

    async def execute(self, arguments, context=None):
        return {"echo": arguments, "task_id": context["task_id"]}


class Agent:
    async def run(self, goal, plan, context):
        return {"goal": goal}


def test_coordinator_routes_tool_result_into_execution_result_and_memory():
    async def scenario():
        registry = AutoToolRegistry()
        registry.register(EchoTool())
        memory = type("Memory", (), {"recall": lambda self, query: [], "remember": lambda self, item, permanent=False: None})()
        coordinator = ExecutionCoordinator(
            agent_runner=Agent(),
            tool_manager=ExecutionToolAdapter(registry),
            memory=memory,
        )
        result = await coordinator.execute({
            "task_id": "tool-flow-1",
            "goal": "echo",
            "tool": "echo",
            "arguments": {"value": 42},
        })
        assert result["status"] == "completed"
        assert result["value"] == {"echo": {"value": 42}, "task_id": "tool-flow-1"}

    asyncio.run(scenario())
