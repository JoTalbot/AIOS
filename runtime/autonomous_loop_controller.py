"""AIOS continuous autonomous loop controller."""

import asyncio


class AutonomousLoopController:
    """Coordinate repeated scheduler cycles with bounded concurrency."""

    def __init__(self, scheduler_loop=None):
        self.scheduler_loop = scheduler_loop
        self.cycles = 0
        self.running = False

    def start_cycle(self):
        self.running = True
        self.cycles += 1
        return {"cycle": self.cycles, "status": "running"}

    async def run_cycle(self):
        """Start workers and drain one autonomous cycle."""
        state = self.start_cycle()
        if self.scheduler_loop is not None:
            await self.scheduler_loop.start()
            await self.scheduler_loop.wait_idle()
        return state

    async def run(self, cycles=None):
        """Run a finite number of cycles, or until stop() is called."""
        completed = 0
        while self.running or completed == 0:
            if cycles is not None and completed >= cycles:
                break
            await self.run_cycle()
            completed += 1
            if cycles is None:
                await asyncio.sleep(0)
        return completed

    async def stop(self):
        self.running = False
        if self.scheduler_loop is not None:
            await self.scheduler_loop.stop()
