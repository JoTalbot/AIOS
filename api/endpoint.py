"""API endpoint boundary for the vNext runtime."""


class AgentEndpoint:
    def __init__(self, service):
        self.service = service

    async def invoke(self, request):
        return await self.service.execute(request)


async def invoke(request, pipeline=None):
    """Dispatch an API request through the configured runtime pipeline."""
    if pipeline is None:
        return request
    if hasattr(pipeline, "handle"):
        return await pipeline.handle(request)
    if callable(pipeline):
        value = pipeline(request)
        if hasattr(value, "__await__"):
            value = await value
        return value
    raise TypeError("pipeline must be callable or expose handle(request)")
