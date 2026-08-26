"""AIOS v22.1 Event Bus Adapter.

Provides a boundary adapter between cognitive services and the internal event bus.
"""


class EventBusAdapter:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    def emit(self, event_name, payload):
        return self.event_bus.publish(event_name, payload)

    def subscribe(self, event_name, handler):
        return self.event_bus.subscribe(event_name, handler)
