import asyncio

from execution.persistence import ExecutionStore
from kernel.scheduler import AgentTask, Scheduler, TaskState


class CountingExecutor:
    def __init__(self):
        self.calls = 0

    async def __call__(self, payload):
        self.calls += 1
        return {"answer": payload["goal"]}


def test_scheduler_persists_result_and_restart_does_not_reexecute():
    persistence = ExecutionStore()
    first = CountingExecutor()
    scheduler = Scheduler(executor=first, persistence=persistence)
    task = AgentTask("restart-1", "agent", {"goal": "ship"})

    asyncio.run(scheduler.submit(task))
    asyncio.run(scheduler.run_until_idle())

    assert first.calls == 1
    assert task.state is TaskState.DONE
    assert persistence.load_result("restart-1") is not None

    second = CountingExecutor()
    restarted = Scheduler(executor=second, persistence=persistence)
    restored_task = AgentTask("restart-1", "agent", {"goal": "ship"})
    asyncio.run(restarted.submit(restored_task))

    assert restored_task.state is TaskState.DONE
    assert second.calls == 0
    assert restarted.queue.qsize() == 0
