"""AIOS API endpoint foundation."""

class AgentEndpoint:
    def __init__(self, service):
        self.service = service

    async def invoke(self, request):
        return await self.service.execute(request)
