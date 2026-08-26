"""AIOS end-to-end execution flow integration."""

class ExecutionFlow:
    def __init__(self, runtime=None, service=None):
        self.runtime = runtime
        self.service = service

    async def execute(self, request):
        if self.service:
            return await self.service.handle(request)
        if self.runtime:
            return await self.runtime.execute(request)
        return None
