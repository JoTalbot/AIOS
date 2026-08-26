"""AIOS API server foundation."""

from .endpoint import AgentEndpoint


class APIServer:
    def __init__(self, pipeline=None, service=None):
        self.pipeline = pipeline
        self.endpoint = AgentEndpoint(service) if service is not None else None

    async def handle(self, request):
        if self.endpoint is not None:
            return await self.endpoint.invoke(request)
        from .endpoint import invoke
        return await invoke(request, self.pipeline)

    async def status(self):
        return {
            "system": "AIOS",
            "api": "online"
        }
