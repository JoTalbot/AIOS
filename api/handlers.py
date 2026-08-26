"""API handlers connecting requests to AIOS services."""

class APIHandler:
    def __init__(self, service=None):
        self.service = service

    async def handle(self, request):
        if self.service:
            return await self.service.execute(request)
        return request
