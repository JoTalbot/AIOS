"""Hash-linked audit events for the OpenHands execution trail."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChainEvent:
    event_id: str
    parent_event_id: str | None
    payload: dict[str, Any]
    event_hash: str


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuditChain:
    """In-memory append-only hash chain; persistence is delegated to audit backend."""

    def __init__(self) -> None:
        self._last_hash = "GENESIS"
        self._last_event_id: str | None = None
        self._events: list[ChainEvent] = []

    def append(self, event_id: str, payload: dict[str, Any]) -> ChainEvent:
        body = {"event_id": event_id, "parent_event_id": self._last_event_id, "payload": payload, "parent_hash": self._last_hash}
        event_hash = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        event = ChainEvent(event_id, self._last_event_id, dict(payload), event_hash)
        self._events.append(event)
        self._last_event_id = event_id
        self._last_hash = event_hash
        return event

    def verify(self) -> bool:
        parent_hash = "GENESIS"
        parent_id: str | None = None
        for event in self._events:
            if event.parent_event_id != parent_id:
                return False
            body = {"event_id": event.event_id, "parent_event_id": event.parent_event_id, "payload": event.payload, "parent_hash": parent_hash}
            expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            if event.event_hash != expected:
                return False
            parent_hash, parent_id = event.event_hash, event.event_id
        return True

    @property
    def events(self) -> tuple[ChainEvent, ...]:
        return tuple(self._events)
