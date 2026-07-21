"""AIOS Capability Marketplace v4.1.0-alpha

Simple in-memory + persistent marketplace for discovering and sharing capabilities.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .storage import Database


@dataclass
class MarketplaceCapability:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    author: str = "community"
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    code_snippet: str = ""  # placeholder for actual capability code


class CapabilityMarketplace:
    """Marketplace for capabilities."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self._items: Dict[str, MarketplaceCapability] = {}
        self.version = "9.0.0-alpha.12"
        self._ensure_table()

    def _ensure_table(self):
        if self.db is None:
            return
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS marketplace (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                author TEXT,
                version TEXT,
                tags TEXT,
                downloads INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                code_snippet TEXT
            )
        """)

    def publish(self, name: str, description: str, author: str = "system", 
                tags: Optional[List[str]] = None, code: str = "") -> MarketplaceCapability:
        item = MarketplaceCapability(
            name=name,
            description=description,
            author=author,
            tags=tags or [],
            code_snippet=code
        )
        self._items[item.id] = item
        return item

    def search(self, query: str = "", tag: str = "", limit: int = 20) -> List[MarketplaceCapability]:
        results = list(self._items.values())
        if query:
            q = query.lower()
            results = [r for r in results if q in r.name.lower() or q in r.description.lower()]
        if tag:
            results = [r for r in results if tag in r.tags]
        return results[:limit]

    def get(self, item_id: str) -> Optional[MarketplaceCapability]:
        return self._items.get(item_id)

    def download(self, item_id: str) -> Optional[dict]:
        item = self._items.get(item_id)
        if item:
            item.downloads += 1
            return {"success": True, "capability": item}
        return {"success": False}

    def stats(self) -> dict:
        return {
            "version": self.version,
            "total_capabilities": len(self._items),
            "total_downloads": sum(i.downloads for i in self._items.values())
        }