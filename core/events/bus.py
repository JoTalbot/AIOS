from .event import KernelEvent
from .persistence import EventStore


class EventBus:
    """Central event backbone for AIOS runtime communication."""

    def __init__(self, store=None):
        self.handlers = {}
        self.wildcard_handlers = []
        self.store = store or EventStore()

    def subscribe(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)
        return handler

    def subscribe_all(self, handler):
        self.wildcard_handlers.append(handler)
        return handler

    def publish(self, event, payload=None, source="kernel"):
        if not isinstance(event, KernelEvent):
            event = KernelEvent(
                name=event,
                source=source,
                payload=payload or {}
            )

        self.store.append(event)

        for handler in self.handlers.get(event.name, []):
            handler(event)

        for handler in self.wildcard_handlers:
            handler(event)

        return event

    def replay(self):
        return self.store.replay()
