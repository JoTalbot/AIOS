import pytest

from execution.coordinator import ExecutionCoordinator
from kernel.memory import MemoryOS


class Agent:
    async def run(self, goal, plan, context):
        return {"goal": goal, "steps": len(plan), "ok": True}


class Tools:
    async def execute(self, result, context=None):
        return {**result, "tool": "executed"}


class Events:
    def __init__(self):
        self.items = []

    def publish(self, event, payload=None, source="kernel"):
        self.items.append((event, payload, source))


@pytest.mark.asyncio
async def test_coordinator_connects_agent_tools_memory_and_events():
    memory = MemoryOS()
    events = Events()
    coordinator = ExecutionCoordinator(Agent(), Tools(), memory, events)

    result = await coordinator.execute({"task_id": "t1", "goal": "demo", "plan": [1, 2], "context": {}})

    assert result["status"] == "completed"
    assert result["result"]["tool"] == "executed"
    assert events.items[0][0] == "execution.started"
    assert events.items[-1][0] == "execution.completed"
    assert memory.long_memory[-1]["type"] == "execution_completed"
