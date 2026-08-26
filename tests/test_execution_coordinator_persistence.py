import asyncio

from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore


class Runner:
    def __init__(self):
        self.calls = 0

    async def run(self, goal, plan, context):
        self.calls += 1
        return {"answer": goal}


def test_coordinator_persists_result_and_skips_replay():
    store = ExecutionStore()
    runner = Runner()
    coordinator = ExecutionCoordinator(agent_runner=runner, persistence=store)
    request = {"task_id": "task-1", "goal": "hello"}

    first = asyncio.run(coordinator.execute(request))
    second = asyncio.run(coordinator.execute(request))

    assert first == second
    assert runner.calls == 1
    assert store.load_result("task-1") == first
