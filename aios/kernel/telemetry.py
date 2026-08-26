"""Telemetry primitives for AIOS v20."""

from dataclasses import dataclass, field
from time import time


@dataclass
class TelemetryEvent:
    name: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time)


class Telemetry:
    def __init__(self):
        self.events = []

    def record(self, name, payload=None):
        event = TelemetryEvent(name=name, payload=payload or {})
        self.events.append(event)
        return event
