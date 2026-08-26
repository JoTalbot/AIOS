"""Runtime orchestration hooks.

Provides lightweight hook registration for lifecycle and execution events.
"""

from typing import Callable, Dict, List


class OrchestrationHooks:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, event: str, callback: Callable) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event: str, *args, **kwargs) -> None:
        for callback in self._hooks.get(event, []):
            callback(*args, **kwargs)
