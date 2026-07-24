"""AIOS Audit Logger v3.0.0

Persistent audit logging using SQLite. Falls back to in-memory + JSONL
if no database is provided. Supports rich querying by type, agent,
time range, and decision.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .storage import Database

__all__ = ["AuditLogger"]


class AuditLogger:
    """Logs all constitutional decisions and execution events.

    Persists events to SQLite for durability and queryability.
    Falls back to in-memory list if no Database is given.
    """

    def __init__(self, db: Optional[Database] = None, file_path: str = "audit_log.jsonl"):
        """Initialize AuditLogger."""
        self.db = db
        self.file_path = file_path
        self._in_memory: list[dict] = []

    def record(self, event: dict) -> dict:
        """Record an audit event. Auto-assigns ID and timestamp if missing."""
        event_id = event.get("id") or Database.new_id()
        timestamp = event.get("timestamp") or Database.now_iso()

        event["id"] = event_id
        event["timestamp"] = timestamp

        event_type = event.get("type", "unknown")
        agent_id = event.get("agent_id")
        decision = event.get("decision")

        # Tags from matched articles/policies
        tags = []
        for article in event.get("matched_articles", []):
            tags.append(f"article:{article}")
        for policy in event.get("matched_policies", []):
            tags.append(f"policy:{policy}")

        if self.db:
            self.db.execute(
                """INSERT INTO audit_events
                   (id, event_type, data, timestamp, agent_id, decision, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    event_type,
                    Database.to_json(event),
                    timestamp,
                    agent_id,
                    decision,
                    ",".join(tags) if tags else None,
                ),
            )
        else:
            # Fallback: in-memory + JSONL file
            self._in_memory.append(event)
            try:
                with open(self.file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            except (IOError, OSError):
                pass  # Best-effort audit log — skip if disk is full/unavailable

        return event

    def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        decision: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        """Query audit events with optional filters.

        Args:
            event_type: Filter by event type (e.g. 'execution_decision').
            agent_id: Filter by agent ID.
            decision: Filter by decision (ALLOW/DENY/REVIEW).
            since: ISO timestamp lower bound.
            until: ISO timestamp upper bound.
            limit: Max results.
            offset: Offset for pagination.
        """
        if self.db:
            conditions = []
            params: list[Any] = []

            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)

            if decision:
                conditions.append("decision = ?")
                params.append(decision)

            if since:
                conditions.append("timestamp >= ?")
                params.append(since)

            if until:
                conditions.append("timestamp <= ?")
                params.append(until)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            sql = f"""
                SELECT data FROM audit_events {where}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            rows = self.db.query(sql, tuple(params))
            return [Database.from_json(r["data"]) for r in rows]

        # Fallback: in-memory filter
        results = list(self._in_memory)
        if event_type:
            results = [e for e in results if e.get("type") == event_type]
        if agent_id:
            results = [e for e in results if e.get("agent_id") == agent_id]
        if decision:
            results = [e for e in results if e.get("decision") == decision]
        if since:
            results = [e for e in results if e.get("timestamp", "") >= since]
        if until:
            results = [e for e in results if e.get("timestamp", "") <= until]

        return results[offset : offset + limit]

    def count(self, event_type: str | None = None) -> int:
        """Count events, optionally filtered by type."""
        if self.db:
            if event_type:
                row = self.db.query_one(
                    "SELECT COUNT(*) as cnt FROM audit_events WHERE event_type = ?",
                    (event_type,),
                )
            else:
                row = self.db.query_one("SELECT COUNT(*) as cnt FROM audit_events")
            return row["cnt"] if row else 0

        if event_type:
            return sum(1 for e in self._in_memory if e.get("type") == event_type)
        return len(self._in_memory)

    def stats(self) -> dict:
        """Return audit statistics."""
        if self.db:
            total = self.db.query_one("SELECT COUNT(*) as cnt FROM audit_events")["cnt"]

            by_type = self.db.query(
                "SELECT event_type, COUNT(*) as cnt FROM audit_events "
                "GROUP BY event_type ORDER BY cnt DESC"
            )
            by_decision = self.db.query(
                "SELECT decision, COUNT(*) as cnt FROM audit_events "
                "WHERE decision IS NOT NULL GROUP BY decision ORDER BY cnt DESC"
            )

            return {
                "total_events": total,
                "by_type": {r["event_type"]: r["cnt"] for r in by_type},
                "by_decision": {r["decision"]: r["cnt"] for r in by_decision},
                "storage": "sqlite",
            }

        types: dict[str, int] = {}
        decisions: dict[str, int] = {}
        for e in self._in_memory:
            t = e.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
            d = e.get("decision")
            if d:
                decisions[d] = decisions.get(d, 0) + 1

        return {
            "total_events": len(self._in_memory),
            "by_type": types,
            "by_decision": decisions,
            "storage": "memory",
        }

    def cleanup(self, retention_days: int = 90) -> int:
        """Delete events older than retention_days. Returns deleted count."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

        if self.db:
            cursor = self.db.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff,))
            return cursor.rowcount

        # In-memory cleanup
        before = len(self._in_memory)
        self._in_memory = [e for e in self._in_memory if e.get("timestamp", "") >= cutoff]
        return before - len(self._in_memory)
