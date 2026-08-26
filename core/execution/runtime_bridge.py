"""Bridge between scheduler, pipeline and runtime layers."""


class RuntimeBridge:
    def __init__(self, scheduler, pipeline):
        self.scheduler = scheduler
        self.pipeline = pipeline

    async def submit(self, task):
        return await self.pipeline.run(task)

    async def execute(self, context):
        """Execution boundary compatible runtime adapter."""
        return await self.pipeline.run(context)
