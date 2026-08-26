import asyncio

class TaskScheduler:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def submit(self, task):
        await self.queue.put(task)

    async def next(self):
        return await self.queue.get()
