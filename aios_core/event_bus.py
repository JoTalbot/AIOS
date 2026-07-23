"""AIOS Event Bus v3.0.0

Pub/sub event bus for inter-module communication with SQLite persistence.
Supports typed events, wildcard subscriptions, and persistent event history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from .storage import Database

from .storage import Database

__all__ = ["EventType", "Event", "EventBus"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------


class EventType:
    """Predefined event type constants for the AIOS event bus.

    Use these constants instead of raw strings to avoid typos and enable
    static analysis.  For user-defined events use ``EventType.CUSTOM`` or
    any arbitrary string.
    """

    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Step lifecycle
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"

    # Memory operations
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_DELETED = "memory_deleted"

    # Knowledge graph
    KNOWLEDGE_NODE_ADDED = "knowledge_node_added"
    KNOWLEDGE_RELATION_ADDED = "knowledge_relation_added"

    # Evolution
    EVOLUTION_PROPOSED = "evolution_proposed"
    EVOLUTION_ADVANCED = "evolution_advanced"
    EVOLUTION_DEPLOYED = "evolution_deployed"

    # Approval workflow
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"

    # Constitution
    CONSTITUTION_EVALUATED = "constitution_evaluated"

    # Learning
    LEARNING_RECORDED = "learning_recorded"
    PATTERN_EXTRACTED = "pattern_extracted"

    # Capability
    CAPABILITY_REGISTERED = "capability_registered"
    CAPABILITY_EXECUTED = "capability_executed"

    # System
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"

    # User-defined events
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """Represents a single event on the bus.

    Attributes:
        id:        Auto-generated UUID hex string.
        event_type: The type/category of the event.
        source:    Name of the module that emitted the event.
        data:      Event payload dictionary.
        timestamp: ISO 8601 UTC timestamp.
        metadata:  Optional extra information.
    """

    id: str
    event_type: str
    source: str
    data: dict
    timestamp: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return a plain dictionary representation."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class EventBus:
    """Pub/sub event bus for inter-module communication.

    Supports exact and wildcard (``fnmatch``) subscriptions, synchronous
    handler dispatch in subscription order, and optional SQLite persistence
    of every emitted event.

    Usage::

        bus = EventBus(db)

        def on_task(e): print(e)
        bus.subscribe(EventType.TASK_CREATED, on_task)
        bus.subscribe_pattern("task_*", on_task)
        bus.emit(EventType.TASK_CREATED, "orchestrator", {"task_id": "abc"})
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db

        # Dispatch structures ------------------------------------------------
        # exact_handlers[event_type] = [(sub_id, handler), ...]
        self._exact_handlers: dict[str, list[tuple[str, Callable]]] = {}
        # pattern_handlers = [(sub_id, pattern, handler), ...]
        self._pattern_handlers: list[tuple[str, str, Callable]] = []

        # Subscription registry: sub_id -> {"type": event_type_or_pattern,
        #                                   "handler": handler,
        #                                   "kind": "exact"|"pattern"}
        self._subscriptions: dict[str, dict[str, Any]] = {}

        self._ensure_table()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the ``events`` table and indexes if they don't exist."""
        if self.db is None:
            return
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                   id          TEXT PRIMARY KEY,
                   event_type  TEXT NOT NULL,
                   source      TEXT NOT NULL,
                   data        TEXT NOT NULL,
                   timestamp   TEXT NOT NULL,
                   metadata    TEXT
               )"""
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_type " "ON events(event_type)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp " "ON events(timestamp)")

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, handler: Callable) -> str:
        """Subscribe to an exact event type.

        Args:
            event_type: The exact event type string to listen for.
            handler:    Callable receiving a single ``event_dict`` argument.

        Returns:
            A subscription ID that can be passed to :meth:`unsubscribe`.
        """
        sub_id = Database.new_id()
        self._exact_handlers.setdefault(event_type, []).append((sub_id, handler))
        self._subscriptions[sub_id] = {
            "type": event_type,
            "handler": handler,
            "kind": "exact",
        }
        return sub_id

    def subscribe_pattern(self, pattern: str, handler: Callable) -> str:
        """Subscribe using a wildcard pattern.

        Uses :func:`fnmatch.fnmatch` glob syntax (e.g. ``"task_*"``,
        ``"memory_*"``).

        Args:
            pattern: Glob pattern matched against event types.
            handler: Callable receiving a single ``event_dict`` argument.

        Returns:
            A subscription ID that can be passed to :meth:`unsubscribe`.
        """
        sub_id = Database.new_id()
        self._pattern_handlers.append((sub_id, pattern, handler))
        self._subscriptions[sub_id] = {
            "type": pattern,
            "handler": handler,
            "kind": "pattern",
        }
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription.

        Args:
            subscription_id: ID returned by :meth:`subscribe` or
                :meth:`subscribe_pattern`.

        Returns:
            ``True`` if the subscription existed and was removed,
            ``False`` otherwise.
        """
        sub = self._subscriptions.pop(subscription_id, None)
        if sub is None:
            return False

        if sub["kind"] == "exact":
            event_type = sub["type"]
            handlers = self._exact_handlers.get(event_type)
            if handlers is not None:
                self._exact_handlers[event_type] = [
                    (sid, h) for sid, h in handlers if sid != subscription_id
                ]
                if not self._exact_handlers[event_type]:
                    del self._exact_handlers[event_type]
        else:
            self._pattern_handlers = [
                (sid, p, h) for sid, p, h in self._pattern_handlers if sid != subscription_id
            ]

        return True

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(
        self,
        event_type: str,
        source: str,
        data: dict,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Emit an event to all matching subscribers.

        Handlers are invoked **synchronously** in subscription order.
        Exceptions raised by handlers are caught and logged — they do
        **not** propagate to the caller.

        The event is persisted to SQLite when a database is available.

        Args:
            event_type: Type of the event (prefer ``EventType`` constants).
            source:     Name of the emitting module.
            data:       Event payload dictionary.
            metadata:   Optional extra metadata dictionary.

        Returns:
            The full event dict that was emitted (and persisted).
        """
        event_id = Database.new_id()
        timestamp = Database.now_iso()

        event = Event(
            id=event_id,
            event_type=event_type,
            source=source,
            data=data,
            timestamp=timestamp,
            metadata=metadata or {},
        )
        event_dict = event.to_dict()

        # Persist -----------------------------------------------------------
        if self.db is not None:
            try:
                self.db.execute(
                    """INSERT INTO events
                           (id, event_type, source, data, timestamp, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        event_id,
                        event_type,
                        source,
                        Database.to_json(data),
                        timestamp,
                        Database.to_json(metadata) if metadata else None,
                    ),
                )
            except Exception:
                logger.exception(
                    "Failed to persist event %s (type=%s)",
                    event_id,
                    event_type,
                )

        # Dispatch to exact-match handlers ----------------------------------
        for sub_id, handler in self._exact_handlers.get(event_type, []):
            try:
                handler(event_dict)
            except Exception:
                logger.exception(
                    "Handler error for subscription %s on event type %s",
                    sub_id,
                    event_type,
                )

        # Dispatch to pattern-match handlers --------------------------------
        for sub_id, pattern, handler in self._pattern_handlers:
            if fnmatch(event_type, pattern):
                try:
                    handler(event_dict)
                except Exception:
                    logger.exception(
                        "Pattern handler error for subscription %s "
                        "(pattern=%s) on event type %s",
                        sub_id,
                        pattern,
                        event_type,
                    )

        return event_dict

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def query(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query persisted events with optional filters.

        Results are ordered by timestamp descending (most recent first).

        Args:
            event_type: Filter by exact event type.
            source:     Filter by source module name.
            since:      ISO timestamp lower bound (inclusive).
            until:      ISO timestamp upper bound (inclusive).
            limit:      Maximum number of results.

        Returns:
            List of event dicts.  Empty list when no database is available.
        """
        if self.db is None:
            return []

        conditions: list[str] = []
        params: list[Any] = []

        if event_type is not None:
            conditions.append("event_type = ?")
            params.append(event_type)

        if source is not None:
            conditions.append("source = ?")
            params.append(source)

        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since)

        if until is not None:
            conditions.append("timestamp <= ?")
            params.append(until)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        sql = f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self.db.query(sql, tuple(params))
        return [_row_to_dict(r) for r in rows]

    def get_event(self, event_id: str) -> Optional[dict]:
        """Retrieve a single event by its ID.

        Args:
            event_id: The UUID hex of the event.

        Returns:
            Event dict, or ``None`` if not found or no database.
        """
        if self.db is None:
            return None

        row = self.db.query_one(
            "SELECT * FROM events WHERE id = ?",
            (event_id,),
        )
        if row is None:
            return None
        return _row_to_dict(row)

    def recent(
        self,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Return the most recent events, optionally filtered by type.

        Convenience wrapper around :meth:`query`.

        Args:
            event_type: Optional event type filter.
            limit:      Maximum number of results (default 50).

        Returns:
            List of event dicts, most recent first.
        """
        return self.query(event_type=event_type, limit=limit)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return aggregate statistics for the event bus.

        Returns:
            Dict containing:
            - ``version``: module version string
            - ``storage``: ``"sqlite"`` or ``"none"``
            - ``total_events``: total persisted event count
            - ``by_type``: dict mapping event type to count
            - ``subscriptions``: number of active subscriptions
        """
        result: dict[str, Any] = {
            "version": "3.0.0",
            "storage": "sqlite" if self.db else "none",
            "total_events": 0,
            "by_type": {},
            "subscriptions": len(self._subscriptions),
        }

        if self.db is not None:
            total_row = self.db.query_one("SELECT COUNT(*) AS cnt FROM events")
            result["total_events"] = total_row["cnt"] if total_row else 0

            type_rows = self.db.query(
                "SELECT event_type, COUNT(*) AS cnt FROM events "
                "GROUP BY event_type ORDER BY cnt DESC"
            )
            result["by_type"] = {r["event_type"]: r["cnt"] for r in type_rows}

        return result


# ---------------------------------------------------------------------------
# Helpers (module-level for easy reuse)
# ---------------------------------------------------------------------------


def _row_to_dict(row: dict) -> dict:
    """Convert a raw database row to a fully-deserialized event dict."""
    return {
        "id": row["id"],
        "event_type": row["event_type"],
        "source": row["source"],
        "data": Database.from_json(row["data"]),
        "timestamp": row["timestamp"],
        "metadata": (Database.from_json(row["metadata"]) if row.get("metadata") else {}),
    }
