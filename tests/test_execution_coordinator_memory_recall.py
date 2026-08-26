import asyncio

from execution import ExecutionCoordinator


class Memory:
    def __init__(self):
        self.queries = []
        self.items = []

    def recall(self, query):
        self.queries.append(query)
        return [{"fact": "remembered"}]

    def remember(self, item, permanent=False):
        self.items.append((item, permanent))


class Agent:
    async def run(self, goal, plan, context):
        return {"goal": goal, "memory": context["memory"]}


def test_coordinator_injects_recalled_memory_into_agent_context():
    async def scenario():
        memory = Memory()
        coordinator = ExecutionCoordinator(agent_runner=Agent(), memory=memory)
        result = await coordinator.execute({"task_id": "recall-1", "goal": "find context"})
        assert memory.queries == ["find context"]
        assert result["value"]["memory"] == [{"fact": "remembered"}]

    asyncio.run(scenario())
