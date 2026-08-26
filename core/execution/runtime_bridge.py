"""Bridge between scheduler, pipeline and runtime layers."""

class RuntimeBridge:
    def __init__(self, scheduler, pipeline):
        self.scheduler = scheduler
        self.pipeline = pipeline

    async def submit(self, task):
        return await self.pipeline.run(task)
