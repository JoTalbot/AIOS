"""AIOS v20 runtime events.

Event primitives for kernel/runtime observability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeEvent:
    """Immutable execution lifecycle event."""

    name: str
    payload: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RuntimeEventBus:
    """Minimal event collector before distributed telemetry integration."""

    def __init__(self):
        self.events: list[RuntimeEvent] = []

    def publish(self, event: RuntimeEvent) -> None:
        self.events.append(event)

    def history(self) -> list[RuntimeEvent]:
        return list(self.events)
