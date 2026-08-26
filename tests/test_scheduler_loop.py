import pytest

from kernel.scheduler import AgentTask, Scheduler, TaskState
from runtime.scheduler_loop import SchedulerLoop


@pytest.mark.asyncio
async def test_scheduler_loop_executes_queued_tasks():
    scheduler = Scheduler()
    loop = SchedulerLoop(scheduler, workers=2)

    await scheduler.submit(AgentTask("task-1", "agent-a", {}))
    await scheduler.submit(AgentTask("task-2", "agent-b", {}))
    await loop.run_until_idle()

    assert scheduler.tasks["task-1"].state is TaskState.DONE
    assert scheduler.tasks["task-2"].state is TaskState.DONE
    assert loop.running is False


@pytest.mark.asyncio
async def test_scheduler_loop_rejects_invalid_worker_count():
    scheduler = Scheduler()
    with pytest.raises(ValueError):
        SchedulerLoop(scheduler, workers=0)
