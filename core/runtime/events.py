"""AIOS runtime event bus.

Provides a lightweight event abstraction for agent lifecycle and execution updates.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class RuntimeEvent:
    name: str
    payload: dict[str, Any]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)

    async def publish(self, event: RuntimeEvent):
        for handler in self._handlers.get(event.name, []):
            result = handler(event)
            if hasattr(result, "__await__"):
                await result
