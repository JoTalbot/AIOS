import asyncio

from execution import ExecutionCoordinator


class Memory:
    def __init__(self):
        self.items = []

    def remember(self, item, permanent=False):
        self.items.append((item, permanent))


def test_coordinator_routes_lifecycle_memory_through_adapter():
    async def scenario():
        memory = Memory()
        coordinator = ExecutionCoordinator(memory=memory)
        result = await coordinator.execute({"task_id": "mem-1", "goal": "hello"})
        assert result["status"] == "completed"
        assert memory.items[0][0]["type"] == "execution_started"
        assert memory.items[-1][0]["type"] == "execution_completed"
        assert memory.items[-1][1] is True

    asyncio.run(scenario())
