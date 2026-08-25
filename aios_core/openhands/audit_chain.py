"""Hash-linked audit events with durable, execution-bound checkpoints."""
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


def _checkpoint_hash(sequence: int, last_event_id: str | None, root_hash: str, task_id: str, agent: str, gate_decision: str | None, commit_sha: str | None, diff_hash: str | None) -> str:
    body = {"sequence": sequence, "last_event_id": last_event_id, "root_hash": root_hash, "task_id": task_id, "agent": agent, "gate_decision": gate_decision, "commit_sha": commit_sha, "diff_hash": diff_hash}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChainCheckpoint:
    sequence: int
    last_event_id: str | None
    root_hash: str
    task_id: str = "system"
    agent: str = "system"
    gate_decision: str | None = None
    commit_sha: str | None = None
    diff_hash: str | None = None
    checkpoint_hash: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_hash:
            object.__setattr__(self, "checkpoint_hash", _checkpoint_hash(self.sequence, self.last_event_id, self.root_hash, self.task_id, self.agent, self.gate_decision, self.commit_sha, self.diff_hash))


class AuditChain:
    """Append-only hash chain with cryptographically bound checkpoints."""

    def __init__(self) -> None:
        self._last_hash = "GENESIS"
        self._last_event_id: str | None = None
        self._events: list[ChainEvent] = []
        self._checkpoints: list[ChainCheckpoint] = []

    def append(self, event_id: str, payload: dict[str, Any]) -> ChainEvent:
        event_hash = _hash(event_id, self._last_event_id, payload, self._last_hash)
        event = ChainEvent(event_id, self._last_event_id, dict(payload), event_hash)
        self._events.append(event)
        self._last_event_id, self._last_hash = event_id, event_hash
        return event

    def checkpoint(self, *, task_id: str = "system", agent: str = "system", gate_decision: str | None = None, commit_sha: str | None = None, diff_hash: str | None = None) -> ChainCheckpoint:
        checkpoint = ChainCheckpoint(len(self._events), self._last_event_id, self._last_hash, task_id, agent, gate_decision, commit_sha, diff_hash)
        self._checkpoints.append(checkpoint)
        return checkpoint

    @classmethod
    def from_persisted(cls, events: Iterable[Mapping[str, Any]]) -> "AuditChain":
        chain = cls()
        stored = [dict(event) for event in events]
        ordered = [event for event in stored if event.get("event_hash") and event.get("event_id") and event.get("type") != "openhands.audit_checkpoint"]
        ordered.sort(key=lambda e: (str(e.get("timestamp", "")), str(e.get("event_id", ""))))
        for item in ordered:
            event_id = str(item["event_id"])
            parent_id = item.get("parent_event_id")
            payload = {k: v for k, v in item.items() if k not in {"event_id", "parent_event_id", "event_hash", "id", "timestamp"}}
            chain._events.append(ChainEvent(event_id, parent_id, payload, str(item["event_hash"])))
        chain._restore_checkpoints(stored)
        if not chain.verify():
            raise ValueError("persisted OpenHands audit chain or checkpoint is invalid")
        if chain._events:
            chain._last_event_id = chain._events[-1].event_id
            chain._last_hash = chain._events[-1].event_hash
        return chain

    def _restore_checkpoints(self, stored_events: list[Mapping[str, Any]]) -> None:
        checkpoints = [event for event in stored_events if event.get("type") == "openhands.audit_checkpoint"]
        checkpoints.sort(key=lambda e: (int(e.get("sequence", -1)), str(e.get("last_event_id", ""))))
        for stored in checkpoints:
            try:
                checkpoint_hash = str(stored["checkpoint_hash"])
                checkpoint = ChainCheckpoint(int(stored["sequence"]), stored.get("last_event_id"), str(stored["root_hash"]), str(stored.get("task_id", "system")), str(stored.get("agent", "system")), stored.get("gate_decision"), stored.get("commit_sha"), stored.get("diff_hash"), checkpoint_hash)
            except (KeyError, TypeError, ValueError):
                raise ValueError("invalid persisted OpenHands audit checkpoint") from None
            self._checkpoints.append(checkpoint)

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
        previous_sequence = -1
        for checkpoint in self._checkpoints:
            if checkpoint.sequence < 0 or checkpoint.sequence > len(self._events) or checkpoint.sequence < previous_sequence:
                return False
            expected_checkpoint_hash = _checkpoint_hash(checkpoint.sequence, checkpoint.last_event_id, checkpoint.root_hash, checkpoint.task_id, checkpoint.agent, checkpoint.gate_decision, checkpoint.commit_sha, checkpoint.diff_hash)
            if checkpoint.checkpoint_hash != expected_checkpoint_hash:
                return False
            if checkpoint.sequence == 0:
                if checkpoint.root_hash != "GENESIS" or checkpoint.last_event_id is not None:
                    return False
            else:
                event = self._events[checkpoint.sequence - 1]
                if checkpoint.last_event_id != event.event_id or checkpoint.root_hash != event.event_hash:
                    return False
            previous_sequence = checkpoint.sequence
        return True

    @property
    def events(self) -> tuple[ChainEvent, ...]:
        return tuple(self._events)

    @property
    def checkpoints(self) -> tuple[ChainCheckpoint, ...]:
        return tuple(self._checkpoints)
