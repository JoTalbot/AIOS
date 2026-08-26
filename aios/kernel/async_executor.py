"""Async execution layer for AIOS v20 kernel."""

import asyncio


class AsyncExecutor:
    """Runs kernel operations asynchronously."""

    async def execute(self, operation, *args, **kwargs):
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        return operation(*args, **kwargs)
