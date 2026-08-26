"""Agent execution lifecycle hooks foundation."""

from typing import Callable, Dict, List


class AgentHooks:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, event: str, callback: Callable):
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs):
        for callback in self._hooks.get(event, []):
            callback(*args, **kwargs)
