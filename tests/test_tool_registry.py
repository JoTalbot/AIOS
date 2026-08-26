import pytest

from runtime.tool_registry import ToolPermissionError, ToolRegistry
from runtime.tool_sandbox import ToolExecutionContext, ToolSandbox


async def add(a, b):
    return a + b


@pytest.mark.asyncio
async def test_tool_registry_enforces_permissions():
    registry = ToolRegistry()
    registry.register("add", add, permissions={"compute"})

    with pytest.raises(ToolPermissionError):
        await registry.execute("add", granted_permissions=set(), a=1, b=2)

    assert await registry.execute("add", granted_permissions={"compute"}, a=1, b=2) == 3


@pytest.mark.asyncio
async def test_tool_sandbox_requires_agent_identity():
    registry = ToolRegistry()
    registry.register("add", add)
    sandbox = ToolSandbox(registry)

    with pytest.raises(PermissionError):
        await sandbox.execute("add", ToolExecutionContext(agent_id=""), a=1, b=2)

    assert await sandbox.execute("add", ToolExecutionContext(agent_id="agent-1"), a=2, b=3) == 5
