"""Agent execution lifecycle hooks v3."""

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass
class HookEvent:
    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)


class AgentHooks:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
        self._history: List[HookEvent] = []

    def register(self, event: str, callback: Callable):
        self._hooks.setdefault(event, []).append(callback)

    def unregister(self, event: str, callback: Callable):
        callbacks = self._hooks.get(event, [])
        if callback in callbacks:
            callbacks.remove(callback)

    def emit(self, event: str, *args, **kwargs):
        hook_event = HookEvent(event, payload=kwargs)
        self._history.append(hook_event)
        results = []
        for callback in self._hooks.get(event, []):
            results.append(callback(hook_event, *args, **kwargs))
        return results

    async def emit_async(self, event: str, *args, **kwargs):
        hook_event = HookEvent(event, payload=kwargs)
        self._history.append(hook_event)
        results = []
        for callback in self._hooks.get(event, []):
            result = callback(hook_event, *args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            results.append(result)
        return results

    def history(self):
        return list(self._history)

    def clear_history(self):
        self._history.clear()
