"""Agent execution lifecycle hooks v4."""

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass
class HookEvent:
    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(order=True)
class HookEntry:
    priority: int
    callback: Callable = field(compare=False)


class AgentHooks:
    def __init__(self):
        self._hooks: Dict[str, List[HookEntry]] = {}
        self._history: List[HookEvent] = []

    def register(self, event: str, callback: Callable, priority: int = 0):
        self._hooks.setdefault(event, []).append(HookEntry(priority, callback))
        self._hooks[event].sort()

    def unregister(self, event: str, callback: Callable):
        callbacks = self._hooks.get(event, [])
        self._hooks[event] = [entry for entry in callbacks if entry.callback != callback]

    def emit(self, event: str, *args, **kwargs):
        hook_event = HookEvent(event, payload=kwargs)
        self._history.append(hook_event)
        results = []
        for entry in self._hooks.get(event, []):
            results.append(entry.callback(hook_event, *args, **kwargs))
        return results

    async def emit_async(self, event: str, *args, **kwargs):
        hook_event = HookEvent(event, payload=kwargs)
        self._history.append(hook_event)
        results = []
        for entry in self._hooks.get(event, []):
            result = entry.callback(hook_event, *args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            results.append(result)
        return results

    def history(self):
        return list(self._history)

    def clear_history(self):
        self._history.clear()
