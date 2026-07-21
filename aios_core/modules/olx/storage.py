"""AIOS OLX Android Agent — SQLite persistence for collected ad cards.

Schema v2 adds sighting-based tracking on top of raw card storage:

* ``olx_sightings`` — one row per ad per collection run (price/timestamp),
  giving a full price history per ad.
* ``olx_ads.first_seen_at`` / ``last_seen_at`` / ``sightings_count`` —
  presence bookkeeping.
* ``olx_ads.is_active`` — ads that vanish from the feed are marked inactive
  (typically sold or removed), without losing their history.

Existing v1 databases are migrated in place (columns are added if missing).
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import AdCard

_SCHEMA = """
CREATE TABLE IF NOT EXISTS olx_ads (
    fingerprint TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL,
    currency TEXT,
    city TEXT,
    published_text TEXT,
    published_at TEXT,
    is_top INTEGER NOT NULL DEFAULT 0,
    ad_id TEXT,
    url TEXT,
    query TEXT,
    collected_at TEXT NOT NULL,
    raw_json TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT,
    sightings_count INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_olx_ads_query ON olx_ads(query);
CREATE INDEX IF NOT EXISTS idx_olx_ads_city ON olx_ads(city);
CREATE INDEX IF NOT EXISTS idx_olx_ads_active ON olx_ads(is_active);

CREATE TABLE IF NOT EXISTS olx_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    price REAL,
    is_top INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_olx_sightings_fp ON olx_sightings(fingerprint);

CREATE TABLE IF NOT EXISTS olx_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_key TEXT NOT NULL,
    interlocutor TEXT,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    sent_at TEXT,
    result TEXT
);
CREATE INDEX IF NOT EXISTS idx_olx_outbox_status ON olx_outbox(status);

CREATE TABLE IF NOT EXISTS own_ads (
    fingerprint TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL,
    currency TEXT,
    url TEXT,
    ad_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_views INTEGER,
    last_favorites INTEGER,
    last_messages INTEGER
);

CREATE TABLE IF NOT EXISTS own_ad_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    views INTEGER,
    favorites INTEGER,
    messages INTEGER
);
CREATE INDEX IF NOT EXISTS idx_own_ad_sightings_fp ON own_ad_sightings(fingerprint);

CREATE TABLE IF NOT EXISTS olx_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    min_price REAL,
    max_price REAL,
    city TEXT,
    created_at TEXT NOT NULL,
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS olx_favorites (
    fingerprint TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
);
"""

_V1_MIGRATION_COLUMNS = {
    "first_seen_at": "TEXT",
    "last_seen_at": "TEXT",
    "sightings_count": "INTEGER NOT NULL DEFAULT 1",
    "is_active": "INTEGER NOT NULL DEFAULT 1",
}

_EXPORT_FIELDS = [
    "fingerprint",
    "title",
    "price",
    "currency",
    "city",
    "published_text",
    "is_top",
    "url",
    "query",
    "first_seen_at",
    "last_seen_at",
    "sightings_count",
    "is_active",
]


class OLXStorage:
    """Deduplicating SQLite store for OLX ad cards with price tracking."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.db_path = str(db_path)
        # check_same_thread=False + a write lock make the store safe to share
        # between the REST API loop and background scheduler threads.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.RLock()
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate_v1()

    def _migrate_v1(self) -> None:
        """Add v2 columns to databases created before sightings existed."""
        with self._lock, self._conn:
            existing = {
                row[1] for row in self._conn.execute("PRAGMA table_info(olx_ads)")
            }
            for column, ddl in _V1_MIGRATION_COLUMNS.items():
                if column not in existing:
                    self._conn.execute(
                        f"ALTER TABLE olx_ads ADD COLUMN {column} {ddl}"
                    )
            # Backfill presence timestamps for pre-v2 rows.
            self._conn.execute(
                "UPDATE olx_ads SET first_seen_at = collected_at "
                "WHERE first_seen_at IS NULL"
            )
            self._conn.execute(
                "UPDATE olx_ads SET last_seen_at = collected_at "
                "WHERE last_seen_at IS NULL"
            )

    def save_ads_with_new(
        self, cards: List[AdCard], seen_at: Optional[str] = None
    ) -> "tuple[int, List[str]]":
        """Like :meth:`save_ads`, but also returns the *new* fingerprints."""
        now = seen_at or datetime.now(timezone.utc).isoformat()
        new_fingerprints: List[str] = []
        inserted = 0
        with self._lock:
            with self._conn:
                for card in cards:
                    row = card.to_dict()
                    cursor = self._conn.execute(
                        """
                        INSERT OR IGNORE INTO olx_ads (
                            fingerprint, title, price, currency, city,
                            published_text, published_at, is_top, ad_id, url,
                            query, collected_at, raw_json,
                            first_seen_at, last_seen_at, sightings_count, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
                        """,
                        (
                            row["fingerprint"],
                            row["title"],
                            row["price"],
                            row["currency"],
                            row["city"],
                            row["published_text"],
                            row["published_at"],
                            int(row["is_top"]),
                            row["ad_id"],
                            row["url"],
                            row["query"],
                            now,
                            json.dumps(row["raw_texts"], ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                    if cursor.rowcount:
                        new_fingerprints.append(row["fingerprint"])
                    if not cursor.rowcount:
                        self._conn.execute(
                            """
                            UPDATE olx_ads SET
                                last_seen_at = ?,
                                sightings_count = sightings_count + 1,
                                is_active = 1,
                                price = ?,
                                currency = COALESCE(?, currency),
                                is_top = ?,
                                title = COALESCE(NULLIF(?, ''), title),
                                city = COALESCE(?, city),
                                url = COALESCE(?, url),
                                ad_id = COALESCE(?, ad_id)
                            WHERE fingerprint = ?
                            """,
                            (
                                now,
                                row["price"],
                                row["currency"],
                                int(row["is_top"]),
                                row["title"],
                                row["city"],
                                row["url"],
                                row["ad_id"],
                                row["fingerprint"],
                            ),
                        )
                    inserted += cursor.rowcount
                    self._conn.execute(
                        """
                        INSERT INTO olx_sightings (fingerprint, seen_at, price, is_top)
                        VALUES (?, ?, ?, ?)
                        """,
                        (row["fingerprint"], now, row["price"], int(row["is_top"])),
                    )
        return inserted, new_fingerprints

    def sync_activity(
        self, query: str, seen_fingerprints: List[str]
    ) -> int:
        """Mark ads of ``query`` missing from the latest collection as inactive.

        Returns the number of ads that changed state (were deactivated or
        came back). Passing an empty list deactivates the whole query feed.
        """
        seen = set(seen_fingerprints)
        changed = 0
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT fingerprint, is_active FROM olx_ads WHERE query = ?", (query,)
            ).fetchall()
            for row in rows:
                should_be_active = row["fingerprint"] in seen
                if bool(row["is_active"]) != should_be_active:
                    self._conn.execute(
                        "UPDATE olx_ads SET is_active = ? WHERE fingerprint = ?",
                        (int(should_be_active), row["fingerprint"]),
                    )
                    changed += 1
        return changed

    def price_history(self, fingerprint: str) -> List[Dict[str, object]]:
        """Chronological price log for one ad (earliest first)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT seen_at, price, is_top FROM olx_sightings
                WHERE fingerprint = ? ORDER BY seen_at, id
                """,
                (fingerprint,),
            ).fetchall()
        return [
            {"seen_at": row["seen_at"], "price": row["price"], "is_top": bool(row["is_top"])}
            for row in rows
        ]

    def save_ads(
        self, cards: List[AdCard], seen_at: Optional[str] = None
    ) -> int:
        """Store cards and record a sighting for each one.

        New fingerprints are inserted; known fingerprints get their presence
        timestamps refreshed and their current price updated. Every card adds
        a row to the price-history log. Returns the number of new ads.
        """
        inserted, _new = self.save_ads_with_new(cards, seen_at=seen_at)
        return inserted

    def _row_to_card(self, row: sqlite3.Row) -> AdCard:
        return AdCard(
            title=row["title"],
            price=row["price"],
            currency=row["currency"],
            city=row["city"],
            published_text=row["published_text"],
            published_at=row["published_at"],
            is_top=bool(row["is_top"]),
            ad_id=row["ad_id"],
            url=row["url"],
            query=row["query"],
            raw_texts=json.loads(row["raw_json"] or "[]"),
        )

    def get_ads(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        active_only: Optional[bool] = None,
    ) -> List[AdCard]:
        """Fetch stored cards with optional query/activity filters."""
        sql = "SELECT * FROM olx_ads"
        conditions: List[str] = []
        params: list = []
        if query is not None:
            conditions.append("query = ?")
            params.append(query)
        if active_only is not None:
            conditions.append("is_active = ?")
            params.append(int(active_only))
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY collected_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_card(row) for row in rows]

    def count(
        self, query: Optional[str] = None, active_only: Optional[bool] = None
    ) -> int:
        """Number of stored cards, optionally filtered by query/activity."""
        sql = "SELECT COUNT(*) FROM olx_ads"
        conditions: List[str] = []
        params: list = []
        if query is not None:
            conditions.append("query = ?")
            params.append(query)
        if active_only is not None:
            conditions.append("is_active = ?")
            params.append(int(active_only))
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        with self._lock:
            return self._conn.execute(sql, params).fetchone()[0]

    def queries(self) -> List[str]:
        """Distinct search queries present in the store."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT query FROM olx_ads WHERE query IS NOT NULL ORDER BY query"
            ).fetchall()
        return [row[0] for row in rows]

    # ---- Outbox (guarded messenger replies) ----

    def enqueue_outbox(
        self, chat_key: str, text: str, interlocutor: Optional[str] = None
    ) -> int:
        """Queue a reply draft; returns the outbox row id."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO olx_outbox (chat_key, interlocutor, text, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (chat_key, interlocutor, text, now),
            )
            return cursor.lastrowid

    def outbox_pending(self) -> List[Dict[str, object]]:
        """All drafts waiting for approval/sending, oldest first."""
        return self.outbox_list(status="pending")

    def outbox_list(self, status: Optional[str] = None) -> List[Dict[str, object]]:
        sql = "SELECT * FROM olx_outbox"
        params: list = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY id"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def outbox_mark(
        self, outbox_id: int, status: str, result: Optional[str] = None
    ) -> bool:
        """Transition an outbox row (pending → sent/failed/cancelled)."""
        sent_at = (
            datetime.now(timezone.utc).isoformat() if status == "sent" else None
        )
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE olx_outbox SET status = ?, sent_at = COALESCE(?, sent_at), "
                "result = ? WHERE id = ?",
                (status, sent_at, result, outbox_id),
            )
            return cursor.rowcount > 0

    # ---- Own ads (my listings) ----

    def upsert_own_ad(self, ad, seen_at: Optional[str] = None) -> bool:
        """Insert or refresh one own-ad row and log a stats sighting.

        ``ad`` is an OwnAd-like object with title/price/currency/url/ad_id/
        status/views/*/fingerprint. Returns True when the ad is new.
        """
        now = seen_at or datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO own_ads (
                    fingerprint, title, price, currency, url, ad_id, status,
                    first_seen_at, last_seen_at, last_views, last_favorites, last_messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ad.fingerprint,
                    ad.title,
                    ad.price,
                    ad.currency,
                    ad.url,
                    ad.ad_id,
                    getattr(ad, "status", "active") or "active",
                    now,
                    now,
                    ad.views,
                    ad.favorites,
                    ad.messages,
                ),
            )
            if not cursor.rowcount:
                self._conn.execute(
                    """
                    UPDATE own_ads SET
                        last_seen_at = ?, last_views = ?, last_favorites = ?,
                        last_messages = ?, price = COALESCE(?, price),
                        status = ?, title = COALESCE(NULLIF(?, ''), title)
                    WHERE fingerprint = ?
                    """,
                    (
                        now,
                        ad.views,
                        ad.favorites,
                        ad.messages,
                        ad.price,
                        getattr(ad, "status", "active") or "active",
                        ad.title,
                        ad.fingerprint,
                    ),
                )
            self._conn.execute(
                """
                INSERT INTO own_ad_sightings (fingerprint, seen_at, views, favorites, messages)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ad.fingerprint, now, ad.views, ad.favorites, ad.messages),
            )
        return bool(cursor.rowcount)

    def own_ad_set_status(self, fingerprint: str, status: str) -> bool:
        """Force-set an own-ad status (e.g. 'inactive' after a repost)."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE own_ads SET status = ? WHERE fingerprint = ?",
                (status, fingerprint),
            )
            return cursor.rowcount > 0

    def own_ads(self, status: Optional[str] = None) -> List[Dict[str, object]]:
        sql = "SELECT * FROM own_ads"
        params: list = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY last_seen_at DESC"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def own_ad_history(self, fingerprint: str) -> List[Dict[str, object]]:
        """Chronological stats log for one own ad (earliest first)."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT seen_at, views, favorites, messages FROM own_ad_sightings
                WHERE fingerprint = ? ORDER BY seen_at, id
                """,
                (fingerprint,),
            ).fetchall()
        return [dict(row) for row in rows]

    # ---- Search subscriptions & favorites ----

    def subscription_add(
        self,
        name: str,
        query: str,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        city: Optional[str] = None,
    ) -> int:
        """Save a named search subscription (filters for new-ad alerts)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO olx_subscriptions
                    (name, query, min_price, max_price, city, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, query, min_price, max_price, city, now),
            )
            return cursor.lastrowid

    def subscriptions_list(self) -> List[Dict[str, object]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM olx_subscriptions ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def subscription_remove(self, subscription_id: int) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM olx_subscriptions WHERE id = ?", (subscription_id,)
            )
            return cursor.rowcount > 0

    def subscription_touch(self, subscription_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE olx_subscriptions SET last_checked_at = ? WHERE id = ?",
                (now, subscription_id),
            )

    def favorite_add(self, fingerprint: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO olx_favorites (fingerprint, added_at) VALUES (?, ?)",
                (fingerprint, now),
            )
            return cursor.rowcount > 0

    def favorite_remove(self, fingerprint: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM olx_favorites WHERE fingerprint = ?", (fingerprint,)
            )
            return cursor.rowcount > 0

    def favorites_list(self) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT fingerprint FROM olx_favorites ORDER BY added_at"
            ).fetchall()
        return [row[0] for row in rows]

    # ---- Export ----

    def _export_rows(self, query: Optional[str]) -> List[Dict[str, object]]:
        ads = self.get_ads(query=query)
        extra: Dict[str, Dict[str, object]] = {}
        with self._lock:
            for row in self._conn.execute(
                "SELECT fingerprint, first_seen_at, last_seen_at, "
                "sightings_count, is_active FROM olx_ads"
            ):
                extra[row["fingerprint"]] = dict(row)
        items: List[Dict[str, object]] = []
        for ad in ads:
            data = ad.to_dict()
            data.update(extra.get(data["fingerprint"], {}))
            items.append({field: data.get(field) for field in _EXPORT_FIELDS})
        return items

    def export_json(self, query: Optional[str] = None) -> str:
        """Export stored ads as a JSON array string."""
        return json.dumps(self._export_rows(query), ensure_ascii=False, indent=2)

    def export_csv(self, query: Optional[str] = None) -> str:
        """Export stored ads as CSV text with a header row."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_EXPORT_FIELDS)
        writer.writeheader()
        for row in self._export_rows(query):
            writer.writerow(row)
        return buffer.getvalue()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "OLXStorage":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
