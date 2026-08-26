"""Graceful shutdown coordination for AIOS vNext runtime resources."""

import asyncio
from typing import Any


class ShutdownManager:
    def __init__(self):
        self._tasks: set[asyncio.Task] = set()
        self._closers: list[Any] = []
        self._closed = False

    def track_task(self, task: asyncio.Task):
        if self._closed:
            task.cancel()
            return task
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def register(self, resource: Any):
        if self._closed:
            return resource
        self._closers.append(resource)
        return resource

    async def shutdown(self):
        if self._closed:
            return {"status": "stopped"}
        self._closed = True
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for resource in reversed(self._closers):
            close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
            if close:
                result = close()
                if asyncio.iscoroutine(result):
                    await result
        self._tasks.clear()
        self._closers.clear()
        return {"status": "stopped"}
