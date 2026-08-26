"""API endpoint boundary for the vNext runtime."""


class AgentEndpoint:
    def __init__(self, service):
        self.service = service

    async def invoke(self, request):
        result = self.service.execute(request)
        if hasattr(result, "__await__"):
            result = await result
        return result


async def invoke(request, pipeline=None):
    """Dispatch an API request through the configured runtime pipeline."""
    if pipeline is None:
        return request
    if hasattr(pipeline, "handle"):
        value = pipeline.handle(request)
        return await value if hasattr(value, "__await__") else value
    if callable(pipeline):
        value = pipeline(request)
        return await value if hasattr(value, "__await__") else value
    raise TypeError("pipeline must be callable or expose handle(request)")
