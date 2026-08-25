"""Structured, non-mutating audit events for kernel decisions."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any


class AuditLogger:
    """Minimal in-memory audit sink for AIOS v20 kernel decisions."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, event: Any) -> dict[str, Any]:
        """Store a normalized event without mutating the caller's object."""
        if is_dataclass(event) and not isinstance(event, type):
            payload = asdict(event)
        elif isinstance(event, dict):
            payload = dict(event)
        else:
            raise TypeError("audit event must be a dataclass instance or dict")
        payload["timestamp"] = datetime.now(UTC).isoformat()
        self.events.append(payload)
        return dict(payload)

    def get_events(self) -> list[dict[str, Any]]:
        """Return defensive copies of recorded events."""
        return [dict(event) for event in self.events]
