"""AIOS API router foundation."""

class Router:
    def __init__(self):
        self.routes = {}

    def register(self, path, handler):
        self.routes[path] = handler

    async def dispatch(self, path, request):
        handler = self.routes[path]
        return await handler(request)
