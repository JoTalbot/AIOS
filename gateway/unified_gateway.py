"""Unified gateway for API and channel entry points."""

class UnifiedGateway:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    async def dispatch(self, request):
        if self.coordinator is None:
            return None
        return await self.coordinator.execute(request)
