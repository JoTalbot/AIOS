"""AIOS scheduler loop integration."""

import asyncio


class SchedulerLoop:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            await asyncio.sleep(0)

    def stop(self):
        self.running = False
