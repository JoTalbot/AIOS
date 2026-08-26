import asyncio

from kernel.runtime_context import RuntimeContext


class Recovery:
    def __init__(self):
        self.calls = 0

    async def restore(self, scheduler):
        self.calls += 1
        return ["restored"]


class Scheduler:
    def __init__(self):
        self._worker_tasks = []
        self.starts = 0
        self.stops = 0

    async def start(self):
        self.starts += 1

    async def stop(self):
        self.stops += 1


class Orchestrator:
    def __init__(self):
        self.calls = 0

    async def run(self, goal, task_id, metadata=None):
        self.calls += 1
        return {"goal": goal, "task_id": task_id}


def test_recovery_is_executed_once_under_concurrent_execute_and_recover():
    async def scenario():
        recovery = Recovery()
        scheduler = Scheduler()
        orchestrator = Orchestrator()
        context = RuntimeContext(scheduler=scheduler, checkpoint_recovery=recovery, orchestrator=orchestrator)
        results = await asyncio.gather(
            context.recover(),
            context.execute("hello", "race-1"),
            context.recover(),
        )
        assert recovery.calls == 1
        assert results[0] == ["restored"]
        assert results[2] == []
        assert orchestrator.calls == 1

    asyncio.run(scenario())
