"""Execution middleware hooks."""

class ExecutionMiddleware:
    async def before(self, context):
        return context

    async def after(self, result):
        return result
