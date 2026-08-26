import pytest

from execution.recovery import RecoveryEngine
from kernel.scheduler import AgentTask, Scheduler, TaskState


class Persistence:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)
        return event


@pytest.mark.asyncio
async def test_scheduler_records_completion_event():
    persistence = Persistence()
    scheduler = Scheduler(persistence=persistence)
    task = AgentTask("task-1", "agent", {})

    await scheduler.submit(task)
    await scheduler.run_until_idle()

    assert task.state is TaskState.DONE
    assert persistence.events[-1]["type"] == "execution.completed"
    assert persistence.events[-1]["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_scheduler_records_recovery_and_failure_events():
    persistence = Persistence()

    async def fail(_):
        raise RuntimeError("fatal")

    scheduler = Scheduler(
        executor=fail,
        recovery=RecoveryEngine(max_retries=0),
        persistence=persistence,
    )
    task = AgentTask("task-2", "agent", {}, max_attempts=1)

    await scheduler.submit(task)
    await scheduler.run_until_idle()

    assert task.state is TaskState.FAILED
    assert [e["type"] for e in persistence.events] == [
        "execution.recovery",
        "execution.failed",
    ]
