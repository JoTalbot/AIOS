import pytest

from execution.recovery import RecoveryEngine
from kernel.scheduler import AgentTask, Scheduler, TaskState


class RestoreExecutor:
    def __init__(self):
        self.calls = 0

    async def __call__(self, payload):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("recoverable")
        assert payload["checkpoint_data"] == "restored"
        return {"restored": True}


@pytest.mark.asyncio
async def test_scheduler_restores_checkpoint_after_retry_budget():
    executor = RestoreExecutor()
    scheduler = Scheduler(executor=executor, recovery=RecoveryEngine(max_retries=1))
    task = AgentTask(
        "restore-1", "agent", {"goal": "test"}, max_attempts=1,
        checkpoint={"checkpoint_data": "restored"},
    )

    await scheduler.submit(task)
    await scheduler.run_until_idle()

    assert task.state is TaskState.DONE
    assert task.attempts == 2
    assert task.payload["result"]["restored"] is True
