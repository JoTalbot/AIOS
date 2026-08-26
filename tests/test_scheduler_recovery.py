import pytest

from kernel.scheduler import AgentTask, Scheduler, TaskState


class FlakyExecutor:
    def __init__(self):
        self.calls = 0

    async def __call__(self, payload):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return {"ok": True}


@pytest.mark.asyncio
async def test_scheduler_retries_transient_execution_failure():
    executor = FlakyExecutor()
    scheduler = Scheduler(executor=executor)
    task = AgentTask("retry-1", "agent", {"goal": "test"}, max_attempts=3)

    await scheduler.submit(task)
    await scheduler.run_until_idle()

    assert task.state is TaskState.DONE
    assert task.attempts == 2
    assert task.payload["result"]["ok"] is True
    assert len(task.history) == 1
