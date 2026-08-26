"""Federation event stream primitives."""

from dataclasses import dataclass


@dataclass
class FederationEvent:
    event_type: str
    source: str
    data: object


class FederationEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event: FederationEvent):
        self.events.append(event)
