"""DevicePool — пул устройств/эмуляторов с арендой под профили.

Одно устройство обслуживает ровно один профиль в каждый момент времени —
это защищает аккаунты от перекрёстных сессий. Пул хранится в SQLite
(``data/devices.sqlite`` или ``AIOS_DEVICES_DB``) и умеет:

* регистрировать устройства (эмуляторы из bootstrap, физические);
* выдавать аренду ``lease()`` — свободное устройство закрепляется за
  профилем (опционально записывая ``device_serial`` в ProfileStore);
* принимать heartbeats и помечать мёртвые устройства offline
  (``reap_stale``) с автоматическим освобождением их аренд;
* возвращать устройства в пул (``release()``).

Потокобезопасен (RLock + check_same_thread=False).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    serial         TEXT PRIMARY KEY,
    avd_name       TEXT,
    status         TEXT NOT NULL DEFAULT 'idle',
    profile_key    TEXT,
    leased_at      TEXT,
    last_heartbeat TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pool_limits (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
"""

STATUS_IDLE = "idle"
STATUS_BUSY = "busy"
STATUS_OFFLINE = "offline"


class DevicePool:
    """Пул устройств с арендой под профили платформ."""

    def __init__(self, db_path: "Optional[str]" = None):
        # По умолчанию — постоянный файл data/devices.sqlite, чтобы пул
        # переживал перезапуски CLI-процессов; ":memory:" — для тестов.
        self.db_path = db_path or os.environ.get(
            "AIOS_DEVICES_DB", "data/devices.sqlite"
        )
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def __enter__(self) -> "DevicePool":
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
    # реестр                                                               #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # квоты                                                                #
    # ------------------------------------------------------------------ #

    def set_limit(self, key: str, value: int) -> None:
        """Устанавливает квоту пула.

        Известные ключи: ``max_devices`` (всего в пуле),
        ``max_busy:<platform>`` (одновременных аренд платформы),
        ``max_avds`` (сколькими auto-созданными AVD может управлять
        ensure_device). ``None``/отсутствие = без лимита.
        """
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO pool_limits (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, int(value)),
            )

    def limit(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Значение квоты или default."""
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM pool_limits WHERE key = ?", (key,)
            ).fetchone()
        return int(row["value"]) if row else default

    def limits(self) -> Dict[str, int]:
        """Все установленные квоты."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM pool_limits ORDER BY key"
            ).fetchall()
        return {row["key"]: int(row["value"]) for row in rows}

    def count_avds(self) -> int:
        """Сколько устройств пула — auto-созданные AVD (есть avd_name)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM devices WHERE avd_name IS NOT NULL"
            ).fetchone()
        return int(row["c"])

    def _busy_platform(self, platform: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM devices "
                "WHERE status = ? AND profile_key LIKE ?",
                (STATUS_BUSY, f"{platform}:%"),
            ).fetchone()
        return int(row["c"])

    def register(self, serial: str, avd_name: Optional[str] = None) -> Dict:
        """Регистрирует устройство (idle) или обновляет avd_name.

        Raises:
            ValueError: превышена квота ``max_devices``.
        """
        now = self._now()
        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT 1 FROM devices WHERE serial = ?", (serial,)
            ).fetchone()
            max_devices = self.limit("max_devices")
            if existing is None and max_devices is not None:
                total = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM devices"
                ).fetchone()["c"]
                if total >= max_devices:
                    raise ValueError(
                        f"pool quota reached: max_devices={max_devices}"
                    )
            self._conn.execute(
                """
                INSERT INTO devices
                    (serial, avd_name, status, last_heartbeat, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(serial) DO UPDATE SET
                    avd_name = COALESCE(excluded.avd_name, devices.avd_name),
                    last_heartbeat = excluded.last_heartbeat,
                    status = CASE WHEN devices.status = 'offline'
                                  THEN 'idle' ELSE devices.status END
                """,
                (serial, avd_name, STATUS_IDLE, now, now),
            )
        return self.get(serial)

    def get(self, serial: str) -> Optional[Dict]:
        """Запись об устройстве или None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM devices WHERE serial = ?", (serial,)
            ).fetchone()
        return dict(row) if row else None

    def status(self) -> List[Dict]:
        """Все устройства пула (по serial)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM devices ORDER BY serial"
            ).fetchall()
        return [dict(row) for row in rows]

    def heartbeat(self, serial: str) -> bool:
        """Отмечает живость устройства. False, если не зарегистрировано."""
        now = self._now()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE devices SET last_heartbeat = ? WHERE serial = ?",
                (now, serial),
            )
            return bool(cursor.rowcount)

    # ------------------------------------------------------------------ #
    # аренда                                                               #
    # ------------------------------------------------------------------ #

    def lease(
        self,
        profile_key: str,
        serial: Optional[str] = None,
        profile_store=None,
    ) -> Optional[Dict]:
        """Закрепляет устройство за профилем.

        Args:
            profile_key: Ключ профиля (``olx:work``).
            serial: Конкретное устройство или None (выбрать свободное,
                наименее недавно арендованное).
            profile_store: Необязательный ProfileStore — тогда
                ``device_serial`` профиля обновляется в реестре.

        Returns:
            Запись об арендованном устройстве или None, если свободных нет.
        """
        now = self._now()
        platform = profile_key.split(":", 1)[0]
        with self._lock, self._conn:
            if serial is not None:
                row = self._conn.execute(
                    "SELECT * FROM devices WHERE serial = ?", (serial,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"device '{serial}' is not registered")
                if row["status"] == STATUS_BUSY and row["profile_key"] != profile_key:
                    return None
                if row["status"] == STATUS_OFFLINE:
                    return None
                if row["status"] != STATUS_BUSY:
                    busy_cap = self.limit(f"max_busy:{platform}")
                    if (busy_cap is not None
                            and self._busy_platform(platform) >= busy_cap):
                        return None
                chosen = row["serial"]
            else:
                # Идемпотентность: профиль уже держит устройство — продлеваем.
                held = self._conn.execute(
                    "SELECT serial FROM devices WHERE profile_key = ? AND status = ?",
                    (profile_key, STATUS_BUSY),
                ).fetchone()
                if held is not None:
                    self._conn.execute(
                        "UPDATE devices SET leased_at = ?, last_heartbeat = ? "
                        "WHERE serial = ?",
                        (now, now, held["serial"]),
                    )
                    self._sync_profile_store(
                        held["serial"], profile_key, profile_store
                    )
                    return self.get(held["serial"])
                busy_cap = self.limit(f"max_busy:{platform}")
                if busy_cap is not None and self._busy_platform(platform) >= busy_cap:
                    return None
                row = self._conn.execute(
                    "SELECT * FROM devices WHERE status = ? "
                    "ORDER BY COALESCE(leased_at, created_at) ASC LIMIT 1",
                    (STATUS_IDLE,),
                ).fetchone()
                if row is None:
                    return None
                chosen = row["serial"]
            self._conn.execute(
                "UPDATE devices SET status = ?, profile_key = ?, leased_at = ?, "
                "last_heartbeat = ? WHERE serial = ?",
                (STATUS_BUSY, profile_key, now, now, chosen),
            )
        self._sync_profile_store(chosen, profile_key, profile_store)
        return self.get(chosen)

    @staticmethod
    def _sync_profile_store(serial, profile_key, profile_store) -> None:
        """Пишет device_serial в реестр профилей, если он передан."""
        if profile_store is not None and ":" in profile_key:
            platform, name = profile_key.split(":", 1)
            profile_store.update(platform, name, device_serial=serial)

    def release(self, profile_key: str) -> Optional[str]:
        """Снимает аренду профиля. Возвращает освобождённый serial/None."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT serial FROM devices WHERE profile_key = ? AND status = ?",
                (profile_key, STATUS_BUSY),
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE devices SET status = ?, profile_key = NULL "
                "WHERE serial = ?",
                (STATUS_IDLE, row["serial"]),
            )
            return row["serial"]

    def reap_stale(self, max_silence_s: float = 900.0) -> List[str]:
        """Помечает молчащие устройства offline и освобождает их аренды.

        Returns:
            Список serial-ов, переведённых в offline.
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=max_silence_s)
        ).isoformat()
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT serial FROM devices WHERE status != ? AND last_heartbeat < ?",
                (STATUS_OFFLINE, cutoff),
            ).fetchall()
            self._conn.execute(
                "UPDATE devices SET status = ?, profile_key = NULL "
                "WHERE status != ? AND last_heartbeat < ?",
                (STATUS_OFFLINE, STATUS_OFFLINE, cutoff),
            )
        return [row["serial"] for row in rows]

    def device_for(self, profile_key: str) -> Optional[Dict]:
        """Устройство, арендованное профилем (или None)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM devices WHERE profile_key = ? AND status = ?",
                (profile_key, STATUS_BUSY),
            ).fetchone()
        return dict(row) if row else None
