"""Event Store for AIOS v10.6.0.

In-memory event sourcing with snapshots, projections, event types,
aggregate grouping, compaction, and full replay capability.

Classes:
    Event           — individual event with type, data, aggregate
    Snapshot        — point-in-time state capture
    Projection      — derived view from event stream
    EventStore      — enhanced store with snapshots, projections, replay
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Event ────────────────────────────────────────────────────────────────────

@dataclass
class Event:
    """Individual event in the event stream."""
    id: str = ""
    event_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    aggregate_id: Optional[str] = None
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


# ── Snapshot ────────────────────────────────────────────────────────────────

@dataclass
class Snapshot:
    """Point-in-time state capture for fast replay."""
    aggregate_id: str
    state: dict[str, Any]
    version: int  # event version at snapshot time
    timestamp: float = field(default_factory=time.time)


# ── Projection ──────────────────────────────────────────────────────────────

@dataclass
class Projection:
    """Derived view from event stream (e.g., count, sum)."""
    name: str
    handler: Callable[[Event, dict[str, Any]], dict[str, Any]]
    state: dict[str, Any] = field(default_factory=dict)


# ── Event Store ─────────────────────────────────────────────────────────────

class EventStore:
    """Enhanced in-memory event store with snapshots and projections.

    Features:
    - Event append with aggregate grouping
    - Snapshot capture for fast replay
    - Projection handlers for derived views
    - Full state replay from events
    - Compaction (merge events into snapshots)
    - Event querying by type and aggregate
    """

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.snapshots: dict[str, Snapshot] = {}  # aggregate_id → Snapshot
        self.projections: dict[str, Projection] = {}
        self._version_counters: dict[str, int] = {}  # aggregate_id → next version

    # ── Append ──────────────────────────────────────────────────

    def append(self, event_type: str, data: dict[str, Any], aggregate_id: str | None = None,
               metadata: dict[str, Any] | None = None) -> Event:
        """Append an event to the store."""
        # Auto-assign version
        version = 1
        if aggregate_id:
            version = self._version_counters.get(aggregate_id, 0) + 1
            self._version_counters[aggregate_id] = version

        event = Event(
            event_type=event_type,
            data=data,
            aggregate_id=aggregate_id,
            version=version,
            metadata=metadata or {},
        )
        self.events.append(event)

        # Update projections
        for proj in self.projections.values():
            proj.state = proj.handler(event, proj.state)

        return event

    # ── Query ───────────────────────────────────────────────────

    def get_events(self, aggregate_id: str | None = None, event_type: str | None = None,
                   since_version: int = 0, limit: int = 100) -> list[Event]:
        """Query events by aggregate, type, version."""
        results = []
        for event in self.events:
            if aggregate_id and event.aggregate_id != aggregate_id:
                continue
            if event_type and event.event_type != event_type:
                continue
            if event.version <= since_version:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return results

    def get_event_by_id(self, event_id: str) -> Event | None:
        """Return event by ID."""
        for event in self.events:
            if event.id == event_id:
                return event
        return None

    def get_latest_event(self, aggregate_id: str) -> Event | None:
        """Return most recent event for an aggregate."""
        events = self.get_events(aggregate_id=aggregate_id)
        return events[-1] if events else None

    # ── Replay ──────────────────────────────────────────────────

    def replay(self, aggregate_id: str) -> dict[str, Any]:
        """Rebuild state from all events for an aggregate.

        Uses snapshot if available, then replays from snapshot version.
        """
        # Start from snapshot if available
        start_version = 0
        state: dict[str, Any] = {}

        snapshot = self.snapshots.get(aggregate_id)
        if snapshot:
            state = snapshot.state.copy()
            start_version = snapshot.version

        # Replay events after snapshot
        events = self.get_events(aggregate_id=aggregate_id, since_version=start_version)
        for event in events:
            state.update(event.data)

        return state

    def replay_all(self) -> dict[str, dict[str, Any]]:
        """Rebuild state for all aggregates."""
        aggregates = set()
        for event in self.events:
            if event.aggregate_id:
                aggregates.add(event.aggregate_id)

        result = {}
        for agg_id in aggregates:
            result[agg_id] = self.replay(agg_id)
        return result

    # ── Snapshots ───────────────────────────────────────────────

    def create_snapshot(self, aggregate_id: str) -> Snapshot:
        """Create a snapshot from current aggregate state."""
        state = self.replay(aggregate_id)
        version = self._version_counters.get(aggregate_id, 0)
        snapshot = Snapshot(aggregate_id=aggregate_id, state=state, version=version)
        self.snapshots[aggregate_id] = snapshot
        return snapshot

    def get_snapshot(self, aggregate_id: str) -> Snapshot | None:
        """Return snapshot for an aggregate."""
        return self.snapshots.get(aggregate_id)

    def delete_snapshot(self, aggregate_id: str) -> None:
        """Delete a snapshot."""
        del self.snapshots[aggregate_id]

    # ── Projections ─────────────────────────────────────────────

    def register_projection(self, name: str, handler: Callable[[Event, dict[str, Any]], dict[str, Any]]) -> Projection:
        """Register a projection handler."""
        proj = Projection(name=name, handler=handler)
        self.projections[name] = proj
        return proj

    def get_projection(self, name: str) -> dict[str, Any]:
        """Return projection state."""
        proj = self.projections.get(name)
        if proj is None:
            raise KeyError(f"Projection '{name}' not found")
        return proj.state

    def rebuild_projection(self, name: str) -> dict[str, Any]:
        """Rebuild projection from scratch."""
        proj = self.projections.get(name)
        if proj is None:
            raise KeyError(f"Projection '{name}' not found")
        proj.state = {}
        for event in self.events:
            proj.state = proj.handler(event, proj.state)
        return proj.state

    # ── Compaction ──────────────────────────────────────────────

    def compact(self) -> int:
        """Compact: create snapshots for all aggregates, prune old events.

        Returns number of events pruned.
        """
        # Create snapshots for all aggregates
        aggregates = set()
        for event in self.events:
            if event.aggregate_id:
                aggregates.add(event.aggregate_id)

        for agg_id in aggregates:
            self.create_snapshot(agg_id)

        # Count events before pruning
        count_before = len(self.events)

        # Keep only events that have no snapshot (or are newer than snapshot)
        keep: list[Event] = []
        for event in self.events:
            if event.aggregate_id is None:
                keep.append(event)
                continue
            snap = self.snapshots.get(event.aggregate_id)
            if snap and event.version <= snap.version:
                continue  # event covered by snapshot
            keep.append(event)

        self.events = keep
        return count_before - len(self.events)

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        event_types = {}
        for event in self.events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        return {
            "total_events": len(self.events),
            "snapshots": len(self.snapshots),
            "projections": len(self.projections),
            "event_types": event_types,
            "aggregates": len(self._version_counters),
        }
