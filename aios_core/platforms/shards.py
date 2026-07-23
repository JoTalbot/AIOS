"""ShardRouter — шардинг профилей по хостам (rendezvous hashing).

При масштабировании на несколько серверов профиль адресуется
``host/platform/name``: маршрут назначается один раз (или при отказе
хоста) и персистентен — один и тот же профиль всегда ведёт на один и
тот же хост, что критично для sticky-сессий устройств и хранилищ.

Выбор хоста при первой маршрутизации — rendezvous (HRW): хост с
максимальным ``sha256(host|profile_key)``. Переназначение происходит
только при явном ``set_healthy(host, false)``/``remove_host`` или
``reassign(host)``.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shard_hosts (
    host       TEXT PRIMARY KEY,
    base_url   TEXT NOT NULL,
    healthy    INTEGER NOT NULL DEFAULT 1,
    added_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shard_routes (
    profile_key TEXT PRIMARY KEY,
    host        TEXT NOT NULL,
    assigned_at TEXT NOT NULL
);
"""


class ShardRouter:
    """Роутер профилей по хостам-шардам."""

    def __init__(self, db_path: "Optional[str]" = None):
        self.db_path = db_path or os.environ.get("AIOS_SHARDS_DB", ":memory:")
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def __enter__(self) -> "ShardRouter":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ #
    # хосты                                                                #
    # ------------------------------------------------------------------ #

    def add_host(self, host: str, base_url: str) -> Dict:
        """Регистрирует хост-шард (обновляет base_url при повторе)."""
        now = self._now()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO shard_hosts (host, base_url, healthy, added_at) "
                "VALUES (?, ?, 1, ?) "
                "ON CONFLICT(host) DO UPDATE SET base_url = excluded.base_url, "
                "healthy = 1",
                (host, base_url, now),
            )
        return {"host": host, "base_url": base_url, "healthy": True}

    def hosts(self) -> List[Dict]:
        """Все хосты-шарды."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM shard_hosts ORDER BY host"
            ).fetchall()
        return [{**dict(row), "healthy": bool(row["healthy"])} for row in rows]

    def set_healthy(self, host: str, healthy: bool) -> bool:
        """Помечает хост здоровым/больным. False — хост не найден."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE shard_hosts SET healthy = ? WHERE host = ?",
                (int(healthy), host),
            )
            return bool(cursor.rowcount)

    def remove_host(self, host: str) -> bool:
        """Удаляет хост и все его маршруты. True, если существовал."""
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM shard_routes WHERE host = ?", (host,))
            cursor = self._conn.execute(
                "DELETE FROM shard_hosts WHERE host = ?", (host,)
            )
            return bool(cursor.rowcount)

    # ------------------------------------------------------------------ #
    # маршруты                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rendezvous(profile_key: str, hosts: List[Dict]) -> Dict:
        """HRW: хост с максимальным хэшем (стабилен между процессами)."""

        def score(host: Dict) -> str:
            key = f"{host['host']}|{profile_key}".encode("utf-8")
            return hashlib.sha256(key).hexdigest()

        return max(hosts, key=score)

    def route_for(self, profile_key: str) -> Optional[Dict]:
        """Маршрут профиля: {profile_key, host, base_url, url}.

        None — нет здоровых хостов. Маршрут липкий: назначенный хост
        сохраняется, пока он здоров; при болезни/удалении профиль
        автоматически перемещается по новому HRW-выбору.
        """
        with self._lock, self._conn:
            route = self._conn.execute(
                "SELECT r.host, h.base_url, h.healthy FROM shard_routes r "
                "JOIN shard_hosts h ON h.host = r.host "
                "WHERE r.profile_key = ?",
                (profile_key,),
            ).fetchone()
            if route is not None and route["healthy"]:
                return {
                    "profile_key": profile_key,
                    "host": route["host"],
                    "base_url": route["base_url"],
                    "url": f"{route['base_url'].rstrip('/')}/profiles/"
                    f"{profile_key.replace(':', '/')}",
                }
            if route is not None:
                self._conn.execute(
                    "DELETE FROM shard_routes WHERE profile_key = ?",
                    (profile_key,),
                )
            healthy = [
                dict(row)
                for row in self._conn.execute(
                    "SELECT * FROM shard_hosts WHERE healthy = 1"
                ).fetchall()
            ]
            if not healthy:
                return None
            chosen = self._rendezvous(profile_key, healthy)
            self._conn.execute(
                "INSERT OR REPLACE INTO shard_routes "
                "(profile_key, host, assigned_at) VALUES (?, ?, ?)",
                (profile_key, chosen["host"], self._now()),
            )
        return {
            "profile_key": profile_key,
            "host": chosen["host"],
            "base_url": chosen["base_url"],
            "url": f"{chosen['base_url'].rstrip('/')}/profiles/"
            f"{profile_key.replace(':', '/')}",
        }

    def unroute(self, profile_key: str) -> bool:
        """Снимает маршрут профиля (следующий route_for назначит заново)."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM shard_routes WHERE profile_key = ?",
                (profile_key,),
            )
            return bool(cursor.rowcount)

    def reassign(self, host: str) -> int:
        """Сбрасывает все маршруты хоста (число освобождённых)."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM shard_routes WHERE host = ?", (host,)
            )
            return int(cursor.rowcount)
