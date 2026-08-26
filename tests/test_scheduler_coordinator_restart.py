import asyncio

from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.scheduler import AgentTask, Scheduler, TaskState


class Runner:
    def __init__(self):
        self.calls = 0

    async def run(self, goal, plan, context):
        self.calls += 1
        return {"answer": goal}


def test_scheduler_recovery_uses_real_execution_coordinator_once():
    persistence = ExecutionStore()
    runner = Runner()
    coordinator = ExecutionCoordinator(agent_runner=runner, persistence=persistence)

    first = Scheduler(executor=coordinator, persistence=persistence)
    asyncio.run(first.submit(AgentTask("restart-1", "agent", {"goal": "continue", "task_id": "restart-1"})))
    asyncio.run(first.run_until_idle())
    assert runner.calls == 1
    assert persistence.load_result("restart-1") is not None

    second = Scheduler(executor=coordinator, persistence=persistence)
    restored = AgentTask("restart-1", "agent", {"goal": "continue", "task_id": "restart-1"})
    asyncio.run(second.submit(restored))
    assert restored.state is TaskState.DONE
    assert second.queue.qsize() == 0
    assert runner.calls == 1
