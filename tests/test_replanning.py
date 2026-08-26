import pytest

from runtime.replanning import ReflectionReplanner, ReplanningPolicy


class Planner:
    async def create_plan(self, goal):
        return [{"goal": goal, "action": "retry"}]


class Memory:
    def __init__(self):
        self.items = []

    def remember(self, item, permanent=False):
        self.items.append(item)


@pytest.mark.asyncio
async def test_replanning_is_bounded_and_records_failure():
    memory = Memory()
    replanner = ReflectionReplanner(Planner(), memory, ReplanningPolicy(max_attempts=2))

    decision, plan = await replanner.replan("demo", 0, RuntimeError("boom"))
    assert decision.retry is True
    assert plan[0]["action"] == "retry"
    assert memory.items

    decision, plan = await replanner.replan("demo", 2, RuntimeError("boom"))
    assert decision.retry is False
    assert plan is None
