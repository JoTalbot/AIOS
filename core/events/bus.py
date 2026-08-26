from .event import KernelEvent


class EventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def publish(self, event, payload=None, source="kernel"):
        if not isinstance(event, KernelEvent):
            event = KernelEvent(
                name=event,
                source=source,
                payload=payload or {}
            )

        for handler in self.handlers.get(event.name, []):
            handler(event)
