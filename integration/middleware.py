"""Integration middleware chain."""

class MiddlewareChain:
    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)

    async def process(self, context):
        for handler in self.handlers:
            context = await handler(context)
        return context
