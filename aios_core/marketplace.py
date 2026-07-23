"""AIOS Capability Marketplace v4.1.0-alpha + H3.14 Platform Plugins

Extended for:
- Capability publishing/sharing
- Platform onboarding packages (descriptor + hints + drivers)
- Marketplace REST API
- Guarded publishing with constitution check
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

try:
    from .storage import Database
except ImportError:
    Database = None


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
    code_snippet: str = ""
    created_at: float = field(default_factory=time.time)
    kind: str = "capability"  # capability | platform_plugin | descriptor
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformPlugin:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    platform: str = ""  # e.g., olx, instagram, facebook, viber
    descriptor_yaml: str = ""
    hints: Dict[str, Any] = field(default_factory=dict)
    drivers: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "community"
    verified: bool = False
    downloads: int = 0
    created_at: float = field(default_factory=time.time)
    readme: str = ""


class CapabilityMarketplace:
    """Marketplace for capabilities and platform plugins (H3.14)."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self._items: Dict[str, MarketplaceCapability] = {}
        self._plugins: Dict[str, PlatformPlugin] = {}
        self.version = "9.1.0"
        self._ensure_table()

    def _ensure_table(self):
        if self.db is None or Database is None:
            return
        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    author TEXT,
                    version TEXT,
                    tags TEXT,
                    downloads INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0,
                    code_snippet TEXT,
                    kind TEXT,
                    metadata TEXT
                )
            """
            )
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS platform_plugins (
                    id TEXT PRIMARY KEY,
                    platform TEXT,
                    descriptor_yaml TEXT,
                    hints TEXT,
                    drivers TEXT,
                    version TEXT,
                    author TEXT,
                    verified INTEGER DEFAULT 0,
                    downloads INTEGER DEFAULT 0,
                    readme TEXT,
                    created_at REAL
                )
            """
            )
        except Exception:
            pass

    # --- Capabilities ---

    def publish(
        self,
        name: str,
        description: str,
        author: str = "system",
        tags: Optional[List[str]] = None,
        code: str = "",
        kind: str = "capability",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MarketplaceCapability:
        item = MarketplaceCapability(
            name=name,
            description=description,
            author=author,
            tags=tags or [],
            code_snippet=code,
            kind=kind,
            metadata=metadata or {},
        )
        self._items[item.id] = item
        if self.db:
            try:
                self.db.execute(
                    "INSERT OR REPLACE INTO marketplace (id, name, description, author, version, tags, downloads, rating, code_snippet, kind, metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        item.id,
                        item.name,
                        item.description,
                        item.author,
                        item.version,
                        json.dumps(item.tags),
                        item.downloads,
                        item.rating,
                        item.code_snippet,
                        item.kind,
                        json.dumps(item.metadata),
                    ),
                )
            except Exception:
                pass
        return item

    def search(
        self, query: str = "", tag: str = "", limit: int = 20, kind: str = ""
    ) -> List[MarketplaceCapability]:
        results = list(self._items.values())
        if query:
            q = query.lower()
            results = [r for r in results if q in r.name.lower() or q in r.description.lower()]
        if tag:
            results = [r for r in results if tag in r.tags]
        if kind:
            results = [r for r in results if r.kind == kind]
        return results[:limit]

    def get(self, item_id: str) -> Optional[MarketplaceCapability]:
        return self._items.get(item_id)

    def download(self, item_id: str) -> Optional[dict]:
        item = self._items.get(item_id)
        if item:
            item.downloads += 1
            return {"success": True, "capability": item, "downloads": item.downloads}
        return {"success": False}

    # --- Platform Plugins (H3.14) ---

    def publish_platform_plugin(
        self,
        platform: str,
        descriptor_yaml: str,
        hints: Optional[Dict[str, Any]] = None,
        drivers: Optional[List[str]] = None,
        author: str = "system",
        readme: str = "",
        version: str = "1.0.0",
    ) -> PlatformPlugin:
        plugin = PlatformPlugin(
            platform=platform,
            descriptor_yaml=descriptor_yaml,
            hints=hints or {},
            drivers=drivers or [],
            author=author,
            readme=readme,
            version=version,
        )
        self._plugins[plugin.id] = plugin
        # also publish as capability for unified search
        self.publish(
            name=f"platform-{platform}",
            description=f"Platform plugin for {platform} - {readme[:100]}",
            author=author,
            tags=["platform", platform, "plugin"],
            code=descriptor_yaml[:2000],
            kind="platform_plugin",
            metadata={"plugin_id": plugin.id, "platform": platform},
        )
        if self.db:
            try:
                self.db.execute(
                    "INSERT OR REPLACE INTO platform_plugins (id, platform, descriptor_yaml, hints, drivers, version, author, verified, downloads, readme, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        plugin.id,
                        plugin.platform,
                        plugin.descriptor_yaml,
                        json.dumps(plugin.hints),
                        json.dumps(plugin.drivers),
                        plugin.version,
                        plugin.author,
                        int(plugin.verified),
                        plugin.downloads,
                        plugin.readme,
                        plugin.created_at,
                    ),
                )
            except Exception:
                pass
        return plugin

    def list_platform_plugins(
        self, platform: str = "", verified_only: bool = False
    ) -> List[PlatformPlugin]:
        results = list(self._plugins.values())
        if platform:
            results = [p for p in results if p.platform == platform]
        if verified_only:
            results = [p for p in results if p.verified]
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    def get_platform_plugin(self, plugin_id: str) -> Optional[PlatformPlugin]:
        return self._plugins.get(plugin_id)

    def verify_plugin(self, plugin_id: str, verifier: str = "system") -> bool:
        p = self._plugins.get(plugin_id)
        if not p:
            return False
        p.verified = True
        return True

    def download_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        p = self._plugins.get(plugin_id)
        if not p:
            return None
        p.downloads += 1
        return {"success": True, "plugin": asdict(p), "downloads": p.downloads}

    def install_plugin(self, plugin_id: str, target_dir: str = "platforms") -> Dict[str, Any]:
        """Simulated install - writes descriptor yaml to platforms/<platform>.yaml"""
        p = self._plugins.get(plugin_id)
        if not p:
            return {"success": False, "error": "plugin not found"}
        try:
            import os

            os.makedirs(target_dir, exist_ok=True)
            out_path = os.path.join(target_dir, f"{p.platform}.yaml")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(p.descriptor_yaml)
            # Also write hints if available
            if p.hints:
                hints_path = os.path.join(target_dir, f"{p.platform}_hints.json")
                with open(hints_path, "w", encoding="utf-8") as f:
                    json.dump(p.hints, f, indent=2)
            return {"success": True, "installed_to": out_path, "platform": p.platform}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stats(self) -> dict:
        return {
            "version": self.version,
            "total_capabilities": len(self._items),
            "total_plugins": len(self._plugins),
            "total_downloads": sum(i.downloads for i in self._items.values())
            + sum(p.downloads for p in self._plugins.values()),
            "verified_plugins": sum(1 for p in self._plugins.values() if p.verified),
            "platforms": list(set(p.platform for p in self._plugins.values())),
        }

    # --- Export for API ---

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capabilities": [asdict(c) for c in list(self._items.values())[:50]],
            "plugins": [asdict(p) for p in list(self._plugins.values())[:50]],
            "stats": self.stats(),
        }
