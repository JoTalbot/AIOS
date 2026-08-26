import asyncio

from kernel.runtime_context import RuntimeContext


def test_concurrent_restart_async_is_serialized():
    async def scenario():
        class Scheduler:
            def __init__(self):
                self._worker_tasks = []
                self.starts = 0
                self.stops = 0
            async def start(self):
                self.starts += 1
            async def stop(self):
                self.stops += 1

        scheduler = Scheduler()
        context = RuntimeContext(scheduler=scheduler)
        await asyncio.gather(context.restart_async(), context.restart_async())
        assert scheduler.starts == 2
        assert scheduler.stops == 2

    asyncio.run(scenario())
