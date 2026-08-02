from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable):
        self._handlers[event_name].append(handler)

    def publish(self, event_name: str, data: Any = None):
        for handler in self._handlers[event_name]:
            handler(data)
