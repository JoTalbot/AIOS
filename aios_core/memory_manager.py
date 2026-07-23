"""AIOS Memory Manager v3.0.0

Persistent memory storage with 3 constitutional categories:
- personal: user-controlled, never federated
- operational: system procedures and lessons learned
- constitutional: immutable principles

All data persisted to SQLite with search, tagging, and TTL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .storage import Database

__all__ = ["MemoryManager"]

_VALID_CATEGORIES = {"personal", "operational", "constitutional"}


class MemoryManager:
    """Manages memory storage, retrieval, and search.

    Memory items are stored in SQLite with category separation
    as required by Core Principle 3 (Memory Separation).
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db

    def store(
        self,
        content: dict,
        category: str = "operational",
        tags: Optional[list[str]] = None,
        source: str | None = None,
        confidence: float = 1.0,
        ttl_seconds: int | None = None,
        metadata: Optional[dict] = None,
        owner_id: str | None = None,
    ) -> dict:
        """Store a memory item.

        Args:
            content: The memory content (any dict).
            category: personal | operational | constitutional.
            tags: List of tags for search.
            source: Where this memory came from.
            confidence: Confidence score 0.0-1.0.
            ttl_seconds: Time-to-live in seconds. None = no expiry.
            metadata: Additional metadata.

        Returns:
            Stored item with id, category, timestamps.
        """
        if category not in _VALID_CATEGORIES:
            category = "operational"

        item_id = Database.new_id()
        now = Database.now_iso()
        expires_at = None
        if ttl_seconds is not None:
            from datetime import timedelta

            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()

        if self.db:
            self.db.execute(
                """INSERT INTO memory_items
                   (id, category, content, tags, source, confidence,
                    created_at, expires_at, metadata, owner_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    category,
                    Database.to_json(content),
                    ",".join(tags) if tags else None,
                    source,
                    confidence,
                    now,
                    expires_at,
                    Database.to_json(metadata) if metadata else None,
                    owner_id,
                ),
            )

        return {
            "id": item_id,
            "category": category,
            "content": content,
            "tags": tags,
            "source": source,
            "confidence": confidence,
            "created_at": now,
            "expires_at": expires_at,
            "owner_id": owner_id,
        }

    def retrieve(
        self, item_id: str, requester_id: str | None = None, is_admin: bool = False
    ) -> Optional[dict]:
        """Retrieve an item, enforcing ownership when a requester is supplied."""
        if self.db is None:
            return None
        row = self.db.query_one("SELECT * FROM memory_items WHERE id = ?", (item_id,))
        if row is None:
            return None
        item = self._row_to_dict(row)
        if (
            requester_id is not None
            and item["category"] == "personal"
            and not is_admin
            and item.get("owner_id") != requester_id
        ):
            return None
        return item

    def search(
        self,
        query: str = "",
        category: str | None = None,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
        requester_id: str | None = None,
        is_admin: bool = False,
    ) -> list[dict]:
        """Search memory items by text query, category, and/or tag.

        Uses SQLite LIKE for text search across content JSON.
        """
        if self.db is None:
            return []

        conditions = []
        params: list[Any] = []

        # Text search in content JSON
        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")

        if category:
            if category in _VALID_CATEGORIES:
                conditions.append("category = ?")
                params.append(category)

        # Personal records are private whenever a caller identity is supplied.
        # Legacy owner-less personal records are visible only to administrators.
        if requester_id is not None and not is_admin:
            conditions.append("(category != 'personal' OR owner_id = ?)")
            params.append(requester_id)

        if tag:
            conditions.append("(tags IS NOT NULL AND tags LIKE ?)")
            params.append(f"%{tag}%")

        # Exclude expired
        conditions.append("(expires_at IS NULL OR expires_at > ?)")
        params.append(Database.now_iso())

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT * FROM memory_items {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.db.query(sql, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def update(
        self,
        item_id: str,
        content: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        confidence: float | None = None,
        requester_id: str | None = None,
        is_admin: bool = False,
    ) -> Optional[dict]:
        """Update an existing memory item."""
        if self.db is None:
            return None

        item = self.retrieve(item_id, requester_id=requester_id, is_admin=is_admin)
        if item is None:
            return None

        # Constitutional memory should not be modified
        if item["category"] == "constitutional":
            return item  # Silent no-op

        new_content = content if content is not None else item["content"]
        new_tags = ",".join(tags) if tags is not None else item.get("_tags_db")

        sets = ["content = ?", "updated_at = ?"]
        vals: list[Any] = [Database.to_json(new_content), Database.now_iso()]

        if tags is not None:
            sets.append("tags = ?")
            vals.append(new_tags)

        if confidence is not None:
            sets.append("confidence = ?")
            vals.append(confidence)

        vals.append(item_id)
        self.db.execute(
            f"UPDATE memory_items SET {', '.join(sets)} WHERE id = ?",
            tuple(vals),
        )
        return self.retrieve(item_id)

    def delete(
        self, item_id: str, requester_id: str | None = None, is_admin: bool = False
    ) -> bool:
        """Delete a memory item, enforcing owner access when supplied."""
        if self.db is None:
            return False

        item = self.retrieve(item_id, requester_id=requester_id, is_admin=is_admin)
        if item is None:
            return False

        # Constitutional memory is immutable
        if item["category"] == "constitutional":
            return False

        cursor = self.db.execute(
            "DELETE FROM memory_items WHERE id = ? AND category != 'constitutional'",
            (item_id,),
        )
        return cursor.rowcount > 0

    def get_by_category(self, category: str, limit: int = 100) -> list[dict]:
        """Get all items in a category."""
        return self.search(category=category, limit=limit)

    def count(self, category: str | None = None) -> int:
        """Count memory items, optionally by category."""
        if self.db is None:
            return 0
        if category:
            row = self.db.query_one(
                "SELECT COUNT(*) as cnt FROM memory_items WHERE category = ? "
                "AND (expires_at IS NULL OR expires_at > ?)",
                (category, Database.now_iso()),
            )
        else:
            row = self.db.query_one(
                "SELECT COUNT(*) as cnt FROM memory_items "
                "WHERE expires_at IS NULL OR expires_at > ?",
                (Database.now_iso(),),
            )
        return row["cnt"] if row else 0

    def cleanup_expired(self) -> int:
        """Delete all expired items. Returns deleted count."""
        if self.db is None:
            return 0
        cursor = self.db.execute(
            "DELETE FROM memory_items WHERE expires_at IS NOT NULL AND expires_at < ?",
            (Database.now_iso(),),
        )
        return cursor.rowcount

    def _row_to_dict(self, row: dict) -> dict:
        """Convert a DB row to a friendly dict."""
        tags_str = row.get("tags")
        tags = tags_str.split(",") if tags_str else []
        return {
            "id": row["id"],
            "category": row["category"],
            "content": Database.from_json(row["content"]),
            "tags": tags,
            "source": row["source"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
            "access_count": row["access_count"],
            "owner_id": row.get("owner_id"),
        }

    def stats(self) -> dict:
        """Return memory statistics."""
        if self.db is None:
            return {"by_category": {}, "total": 0, "storage": "none"}

        rows = self.db.query(
            "SELECT category, COUNT(*) as cnt FROM memory_items "
            "WHERE expires_at IS NULL OR expires_at > ? "
            "GROUP BY category",
            (Database.now_iso(),),
        )
        by_category = {r["category"]: r["cnt"] for r in rows}
        return {
            "by_category": by_category,
            "total": sum(by_category.values()),
            "storage": "sqlite",
        }
