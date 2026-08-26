from .event import KernelEvent
from .persistence import EventStore


class EventBus:
    def __init__(self, store=None):
        self.handlers = {}
        self.store = store or EventStore()

    def subscribe(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

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

    def replay(self):
        return self.store.replay()
