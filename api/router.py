"""AIOS API router foundation."""


class Router:
    def __init__(self):
        self.routes = {}

    def register(self, path, handler):
        self.routes[path] = handler

    def register_runtime(self, service, path="/execute"):
        """Register the canonical RuntimeAPIService at the execution route."""
        self.register(path, service.execute)
        return service.execute

    async def dispatch(self, path, request):
        handler = self.routes[path]
        result = handler(request)
        if hasattr(result, "__await__"):
            result = await result
        return result
