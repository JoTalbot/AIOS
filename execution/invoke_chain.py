"""Unified AIOS invocation chain foundation."""

class InvocationChain:
    def __init__(self, runtime):
        self.runtime = runtime

    async def execute(self, request):
        return await self.runtime.execute(request)
