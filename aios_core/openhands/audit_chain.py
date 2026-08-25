"""Hash-linked audit events for the OpenHands execution trail."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ChainEvent:
    event_id: str
    parent_event_id: str | None
    payload: dict[str, Any]
    event_hash: str


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(event_id: str, parent_event_id: str | None, payload: dict[str, Any], parent_hash: str) -> str:
    body = {"event_id": event_id, "parent_event_id": parent_event_id, "payload": payload, "parent_hash": parent_hash}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


class AuditChain:
    """Append-only hash chain with restoration from persisted audit events."""

    def __init__(self) -> None:
        self._last_hash = "GENESIS"
        self._last_event_id: str | None = None
        self._events: list[ChainEvent] = []

    def append(self, event_id: str, payload: dict[str, Any]) -> ChainEvent:
        event_hash = _hash(event_id, self._last_event_id, payload, self._last_hash)
        event = ChainEvent(event_id, self._last_event_id, dict(payload), event_hash)
        self._events.append(event)
        self._last_event_id, self._last_hash = event_id, event_hash
        return event

    @classmethod
    def from_persisted(cls, events: Iterable[Mapping[str, Any]]) -> "AuditChain":
        chain = cls()
        ordered = [dict(event) for event in events if event.get("event_hash") and event.get("event_id")]
        ordered.sort(key=lambda e: e.get("timestamp", ""))
        for stored in ordered:
            event_id = str(stored["event_id"])
            parent_id = stored.get("parent_event_id")
            payload = {k: v for k, v in stored.items() if k not in {"event_id", "parent_event_id", "event_hash", "id", "timestamp"}}
            event = ChainEvent(event_id, parent_id, payload, str(stored["event_hash"]))
            chain._events.append(event)
            chain._last_event_id, chain._last_hash = event_id, event.event_hash
        return chain

    def verify(self) -> bool:
        parent_hash = "GENESIS"
        parent_id: str | None = None
        for event in self._events:
            if event.parent_event_id != parent_id:
                return False
            expected = _hash(event.event_id, event.parent_event_id, event.payload, parent_hash)
            if event.event_hash != expected:
                return False
            parent_hash, parent_id = event.event_hash, event.event_id
        return True

    @property
    def events(self) -> tuple[ChainEvent, ...]:
        return tuple(self._events)
