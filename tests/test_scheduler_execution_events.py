import asyncio

from execution.events import EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_RECOVERY
from kernel.scheduler import AgentTask, Scheduler, TaskState


class Persistence:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)
        return event


def test_scheduler_records_canonical_success_event():
    async def run():
        persistence = Persistence()
        scheduler = Scheduler(persistence=persistence)
        task = AgentTask("task-1", "agent", {})
        await scheduler.submit(task)
        await scheduler.run_until_idle()
        await scheduler.stop()
        assert task.state is TaskState.DONE
        assert persistence.events[-1]["type"] == EXECUTION_COMPLETED

    asyncio.run(run())


def test_scheduler_records_recovery_then_failure():
    async def run():
        persistence = Persistence()

        async def fail(_payload):
            raise RuntimeError("boom")

        scheduler = Scheduler(executor=fail, persistence=persistence)
        task = AgentTask("task-2", "agent", {}, max_attempts=1)
        await scheduler.submit(task)
        await scheduler.run_until_idle()
        await scheduler.stop()
        assert task.state is TaskState.FAILED
        assert [event["type"] for event in persistence.events] == [
            EXECUTION_RECOVERY,
            EXECUTION_FAILED,
        ]

    asyncio.run(run())
