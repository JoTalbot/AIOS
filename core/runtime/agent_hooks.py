"""Agent execution lifecycle hooks v10."""

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
        self._decisions: List[Dict[str, Any]] = []
        self._analytics: List[Dict[str, Any]] = []
        self._observers: List[Callable] = []
        self._mesh_callbacks: List[Callable] = []
        self._observer_events = 0

    def register(self, event: str, callback: Callable, priority: int = 0):
        self._hooks.setdefault(event, []).append(HookEntry(priority, callback))
        self._hooks[event].sort()

    def register_observer(self, callback: Callable):
        self._observers.append(callback)

    def register_mesh_callback(self, callback: Callable):
        self._mesh_callbacks.append(callback)

    def unregister_mesh_callback(self, callback: Callable):
        self._mesh_callbacks = [item for item in self._mesh_callbacks if item != callback]

    def unregister_observer(self, callback: Callable):
        self._observers = [item for item in self._observers if item != callback]

    def unregister(self, event: str, callback: Callable):
        self._hooks[event] = [entry for entry in self._hooks.get(event, []) if entry.callback != callback]

    def _notify_observers(self, event):
        self._observer_events += 1
        for observer in self._observers:
            observer(event)
        for callback in self._mesh_callbacks:
            callback(event)

    def emit(self, event: str, *args, **kwargs):
        hook_event = HookEvent(event, payload=kwargs)
        self._history.append(hook_event)
        self._notify_observers(hook_event)
        return [entry.callback(hook_event, *args, **kwargs) for entry in self._hooks.get(event, [])]

    async def emit_async(self, event: str, *args, **kwargs):
        results = self.emit(event, *args, **kwargs)
        resolved = []
        for result in results:
            if inspect.isawaitable(result):
                result = await result
            resolved.append(result)
        return resolved

    def emit_recovery_decision(self, decision: str, **metadata):
        record = {"decision": decision, **metadata}
        self._decisions.append(record)
        return self.emit("recovery.decision", **record)

    def record_analytics(self, metric: str, value: Any = 1, **metadata):
        record = {"metric": metric, "value": value, **metadata}
        self._analytics.append(record)
        return self.emit("recovery.analytics", **record)

    def analytics(self):
        return list(self._analytics)

    def decisions(self):
        return list(self._decisions)

    def observability(self):
        return {"observers": len(self._observers), "mesh_callbacks": len(self._mesh_callbacks), "events": self._observer_events, "history": len(self._history)}

    def history(self, event: str = None):
        if event is None:
            return list(self._history)
        return [item for item in self._history if item.name == event]

    def clear_history(self):
        self._history.clear()
        self._decisions.clear()
        self._analytics.clear()
        self._observer_events = 0
