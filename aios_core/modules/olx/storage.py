"""AIOS OLX Android Agent — SQLite persistence for collected ad cards."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

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
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_olx_ads_query ON olx_ads(query);
CREATE INDEX IF NOT EXISTS idx_olx_ads_city ON olx_ads(city);
"""


class OLXStorage:
    """Deduplicating SQLite store for OLX ad cards."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def save_ads(self, cards: List[AdCard]) -> int:
        """Insert new cards; known fingerprints are skipped. Returns insert count."""
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        with self._conn:
            for card in cards:
                row = card.to_dict()
                cursor = self._conn.execute(
                    """
                    INSERT OR IGNORE INTO olx_ads (
                        fingerprint, title, price, currency, city,
                        published_text, published_at, is_top, ad_id, url,
                        query, collected_at, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )
                inserted += cursor.rowcount
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
        self, query: Optional[str] = None, limit: Optional[int] = None
    ) -> List[AdCard]:
        """Fetch stored cards, optionally filtered by search query."""
        sql = "SELECT * FROM olx_ads"
        params: list = []
        if query is not None:
            sql += " WHERE query = ?"
            params.append(query)
        sql += " ORDER BY collected_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_card(row) for row in rows]

    def count(self, query: Optional[str] = None) -> int:
        """Number of stored cards, optionally for a single query."""
        if query is None:
            return self._conn.execute("SELECT COUNT(*) FROM olx_ads").fetchone()[0]
        return self._conn.execute(
            "SELECT COUNT(*) FROM olx_ads WHERE query = ?", (query,)
        ).fetchone()[0]

    def queries(self) -> List[str]:
        """Distinct search queries present in the store."""
        rows = self._conn.execute(
            "SELECT DISTINCT query FROM olx_ads WHERE query IS NOT NULL ORDER BY query"
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "OLXStorage":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
