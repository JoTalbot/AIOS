"""AIOS scheduler loop integration.

The loop owns worker lifecycle while Scheduler owns task state and execution.
"""

import asyncio


class SchedulerLoop:
    def __init__(self, scheduler, workers=1):
        if workers < 1:
            raise ValueError("workers must be >= 1")
        self.scheduler = scheduler
        self.workers = workers
        self.running = False
        self._worker_tasks = []

    async def start(self):
        """Start scheduler workers and return once they are running."""
        if self.running:
            return self

        self.running = True
        self._worker_tasks = [
            asyncio.create_task(self.scheduler.worker())
            for _ in range(self.workers)
        ]
        return self

    async def wait_idle(self):
        """Wait until all currently queued tasks have been acknowledged."""
        await self.scheduler.queue.join()

    async def stop(self):
        """Stop workers without losing tasks already submitted to the queue."""
        if not self.running:
            return

        await self.wait_idle()
        self.running = False
        for task in self._worker_tasks:
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    async def run_until_idle(self):
        """Run workers, drain the current queue, then stop them."""
        await self.start()
        await self.wait_idle()
        await self.stop()
