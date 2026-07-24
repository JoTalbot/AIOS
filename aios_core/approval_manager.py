"""AIOS Approval Manager v3.0.0

Persistent approval workflow management using SQLite.
Supports UUID-based IDs, timeout expiration, and rich querying.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .storage import Database


class ApprovalManager:
    """Manages approval workflows for critical actions.

    Approvals persist in SQLite. Pending approvals can expire
    based on configurable timeout.
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        timeout_seconds: int = 86400,
        max_pending: int = 100,
    ):
        """Initialize ApprovalManager."""
        self.db = db
        self.timeout_seconds = timeout_seconds
        self.max_pending = max_pending

    def request(
        self,
        action: dict,
        evaluation_id: str | None = None,
        validation_data: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Request approval for an action.

        Returns the approval record with a UUID-based ID.
        """
        approval_id = Database.new_id()
        now = Database.now_iso()

        if self.db:
            # Check max pending limit
            pending_count = self.db.query_one(
                "SELECT COUNT(*) as cnt FROM approvals WHERE status = 'pending'"
            )["cnt"]
            if pending_count >= self.max_pending:
                raise RuntimeError(f"Max pending approvals ({self.max_pending}) reached")

            self.db.execute(
                """INSERT INTO approvals
                   (id, action_data, status, requested_at, timeout_seconds,
                    evaluation_id, validation_data, metadata)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)""",
                (
                    approval_id,
                    Database.to_json(action),
                    now,
                    self.timeout_seconds,
                    evaluation_id,
                    Database.to_json(validation_data) if validation_data else None,
                    Database.to_json(metadata) if metadata else None,
                ),
            )
            return self._get_by_id(approval_id)

        # Fallback: in-memory
        approval = {
            "id": approval_id,
            "action": action,
            "status": "pending",
            "requested_at": now,
            "resolved_at": None,
            "resolved_by": None,
            "evaluation_id": evaluation_id,
            "validation": validation_data,
            "metadata": metadata,
        }
        return approval

    def approve(self, approval_id: str, resolved_by: str = "human") -> Optional[dict]:
        """Approve a pending action by its UUID."""
        return self._resolve(approval_id, "approved", resolved_by)

    def deny(self, approval_id: str, resolved_by: str = "human") -> Optional[dict]:
        """Deny a pending action by its UUID."""
        return self._resolve(approval_id, "denied", resolved_by)

    def _resolve(self, approval_id: str, new_status: str, resolved_by: str) -> Optional[dict]:
        """Resolve an approval (approve or deny)."""
        if self.db:
            record = self._get_by_id(approval_id)
            if record is None:
                return None
            if record["status"] != "pending":
                return record  # Already resolved

            now = Database.now_iso()
            self.db.execute(
                """UPDATE approvals
                   SET status = ?, resolved_at = ?, resolved_by = ?
                   WHERE id = ? AND status = 'pending'""",
                (new_status, now, resolved_by, approval_id),
            )
            return self._get_by_id(approval_id)

        return None  # In-memory not supported for UUID-based access

    def _get_by_id(self, approval_id: str) -> Optional[dict]:
        """Get a single approval by ID."""
        if self.db:
            row = self.db.query_one("SELECT * FROM approvals WHERE id = ?", (approval_id,))
            if row is None:
                return None
            return self._row_to_dict(row)
        return None

    def _row_to_dict(self, row: dict) -> dict:
        """Convert a DB row to a friendly dict."""
        action = Database.from_json(row["action_data"])
        validation = Database.from_json(row["validation_data"]) if row["validation_data"] else None
        metadata = Database.from_json(row["metadata"]) if row["metadata"] else None
        return {
            "id": row["id"],
            "action": action,
            "status": row["status"],
            "requested_at": row["requested_at"],
            "resolved_at": row["resolved_at"],
            "resolved_by": row["resolved_by"],
            "timeout_seconds": row["timeout_seconds"],
            "evaluation_id": row["evaluation_id"],
            "validation": validation,
            "metadata": metadata,
        }

    def get_pending(self, limit: int = 100) -> list[dict]:
        """Get all pending approvals."""
        if self.db:
            self._expire_timeouts()
            rows = self.db.query(
                "SELECT * FROM approvals WHERE status = 'pending' "
                "ORDER BY requested_at ASC LIMIT ?",
                (limit,),
            )
            return [self._row_to_dict(r) for r in rows]
        return []

    def history(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Return approval history, optionally filtered by status."""
        if self.db:
            if status:
                rows = self.db.query(
                    "SELECT * FROM approvals WHERE status = ? "
                    "ORDER BY requested_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset),
                )
            else:
                rows = self.db.query(
                    "SELECT * FROM approvals " "ORDER BY requested_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [self._row_to_dict(r) for r in rows]
        return []

    def _expire_timeouts(self):
        """Mark expired pending approvals as 'expired'."""
        if self.db is None:
            return
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.timeout_seconds)).isoformat()
        now = Database.now_iso()
        self.db.execute(
            """UPDATE approvals
               SET status = 'expired', resolved_at = ?, resolved_by = 'system'
               WHERE status = 'pending' AND requested_at < ?""",
            (now, cutoff),
        )

    def stats(self) -> dict:
        """Return approval statistics."""
        if self.db:
            self._expire_timeouts()
            rows = self.db.query("SELECT status, COUNT(*) as cnt FROM approvals GROUP BY status")
            return {
                "by_status": {r["status"]: r["cnt"] for r in rows},
                "timeout_seconds": self.timeout_seconds,
                "max_pending": self.max_pending,
                "storage": "sqlite",
            }
        return {
            "by_status": {},
            "timeout_seconds": self.timeout_seconds,
            "max_pending": self.max_pending,
            "storage": "none",
        }
