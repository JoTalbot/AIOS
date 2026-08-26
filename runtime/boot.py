import asyncio


class AIOSBoot:
    """Kernel bootstrap sequence."""

    def __init__(self, scheduler, memory):
        self.scheduler = scheduler
        self.memory = memory

    async def start(self):
        worker = asyncio.create_task(self.scheduler.worker())
        return {
            "status": "running",
            "services": ["scheduler", "memory"]
        }, worker
