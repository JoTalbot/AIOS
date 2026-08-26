import asyncio

from execution.tool_adapter import ExecutionToolAdapter
from tools.registry_auto import AutoToolRegistry


class Tool:
    name = "echo"

    async def execute(self, arguments, context=None):
        return {"arguments": arguments, "context": context}


def test_execution_tool_adapter_resolves_and_executes_registry_tool():
    async def scenario():
        registry = AutoToolRegistry()
        registry.register(Tool())
        result = await ExecutionToolAdapter(registry).execute("echo", {"value": 1}, {"task_id": "t1"})
        assert result == {"arguments": {"value": 1}, "context": {"task_id": "t1"}}

    asyncio.run(scenario())


def test_execution_tool_adapter_rejects_unknown_tool():
    async def scenario():
        try:
            await ExecutionToolAdapter(AutoToolRegistry()).execute("missing")
        except KeyError as error:
            assert "unknown tool" in str(error)
        else:
            raise AssertionError("expected unknown tool error")

    asyncio.run(scenario())
