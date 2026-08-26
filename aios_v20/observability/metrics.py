"""AIOS v20 Observability Metrics Layer.

Collects runtime and governance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricEvent:
    name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MetricsCollector:
    def __init__(self):
        self.events = []

    def record(self, name: str, value: float = 1.0):
        event = MetricEvent(name=name, value=value)
        self.events.append(event)
        return event

    def list_events(self):
        return self.events
