"""ProfileStore — реестр профилей (SQLite).

Хранит описания профилей всех платформ в одном лёгком реестре
(``data/profiles.sqlite`` или ``AIOS_PROFILES_DB``). Данные самих
платформ живут в per-profile SQLite-файлах — реестр только маршрутизирует.
Потокобезопасен (RLock + check_same_thread=False).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .profile import Profile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_profiles (
    platform       TEXT NOT NULL,
    name           TEXT NOT NULL,
    device_serial  TEXT,
    android_user   INTEGER NOT NULL DEFAULT 0,
    db_path        TEXT,
    locale         TEXT NOT NULL DEFAULT 'uk-UA',
    notes          TEXT NOT NULL DEFAULT '',
    is_default     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    PRIMARY KEY (platform, name)
);
CREATE INDEX IF NOT EXISTS idx_platform_profiles_default
    ON platform_profiles (platform, is_default);
"""

_DEFAULT_STORE: "Optional[ProfileStore]" = None


class ProfileStore:
    """SQLite-реестр профилей платформы."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------ #
    # фабрика по умолчанию                                                 #
    # ------------------------------------------------------------------ #

    @classmethod
    def default(cls) -> "ProfileStore":
        """Process-wide реестр из ``AIOS_PROFILES_DB`` (fallback ``data/profiles.sqlite``)."""
        global _DEFAULT_STORE
        if _DEFAULT_STORE is None:
            _DEFAULT_STORE = cls(os.environ.get("AIOS_PROFILES_DB", "data/profiles.sqlite"))
        return _DEFAULT_STORE

    @classmethod
    def reset_default(cls) -> None:
        """Сбрасывает синглтон (тесты)."""
        global _DEFAULT_STORE
        if _DEFAULT_STORE is not None:
            _DEFAULT_STORE.close()
        _DEFAULT_STORE = None

    def __enter__(self) -> "ProfileStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        """Clean up resources."""
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def add(self, profile: Profile) -> Profile:
        """Создаёт профиль. Ошибка, если ``platform:name`` уже занят."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    """
                    INSERT INTO platform_profiles
                        (platform, name, device_serial, android_user, db_path,
                         locale, notes, is_default, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.platform,
                        profile.name,
                        profile.device_serial,
                        profile.android_user,
                        profile.db_path,
                        profile.locale,
                        profile.notes,
                        int(profile.is_default),
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"profile '{profile.key}' already exists") from None
            if profile.is_default:
                self._set_default_locked(profile.platform, profile.name, now)
        return self.get(profile.platform, profile.name)

    def get(self, platform: str, name: str) -> Optional[Profile]:
        """Профиль по ключу или None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM platform_profiles WHERE platform = ? AND name = ?",
                (platform, name),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def list(self, platform: str | None = None) -> List[Profile]:
        """Все профили (опционально — одной платформы)."""
        sql = "SELECT * FROM platform_profiles"
        params: list = []
        if platform is not None:
            sql += " WHERE platform = ?"
            params.append(platform)
        sql += " ORDER BY platform, name"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def update(self, platform: str, name: str, **fields) -> Optional[Profile]:
        """Точечное обновление полей профиля."""
        allowed = {
            "device_serial",
            "android_user",
            "db_path",
            "locale",
            "notes",
            "is_default",
        }
        patch = {k: v for k, v in fields.items() if k in allowed}
        if not patch:
            return self.get(platform, name)
        now = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join(f"{key} = ?" for key in sorted(patch))
        values = [int(v) if key == "is_default" else v for key, v in sorted(patch.items())]
        with self._lock, self._conn:
            cursor = self._conn.execute(
                f"UPDATE platform_profiles SET {assignments}, updated_at = ? "
                f"WHERE platform = ? AND name = ?",
                (*values, now, platform, name),
            )
            if patch.get("is_default"):
                self._set_default_locked(platform, name, now)
            if not cursor.rowcount:
                return None
        return self.get(platform, name)

    def remove(self, platform: str, name: str) -> bool:
        """Удаляет профиль. True, если существовал."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM platform_profiles WHERE platform = ? AND name = ?",
                (platform, name),
            )
            return bool(cursor.rowcount)

    def set_default(self, platform: str, name: str) -> Optional[Profile]:
        """Делает профиль дефолтом платформы (снимая флаг с остальных)."""
        if self.get(platform, name) is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            self._set_default_locked(platform, name, now)
        return self.get(platform, name)

    def get_default(self, platform: str) -> Optional[Profile]:
        """Профиль по умолчанию платформы или None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM platform_profiles " "WHERE platform = ? AND is_default = 1",
                (platform,),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    # ------------------------------------------------------------------ #
    # internals                                                            #
    # ------------------------------------------------------------------ #

    def _set_default_locked(self, platform: str, name: str, now: str) -> None:
        self._conn.execute(
            "UPDATE platform_profiles SET is_default = 0 WHERE platform = ?",
            (platform,),
        )
        self._conn.execute(
            "UPDATE platform_profiles SET is_default = 1, updated_at = ? "
            "WHERE platform = ? AND name = ?",
            (now, platform, name),
        )

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> Profile:
        return Profile(
            platform=row["platform"],
            name=row["name"],
            device_serial=row["device_serial"],
            android_user=row["android_user"],
            db_path=row["db_path"],
            locale=row["locale"],
            notes=row["notes"],
            is_default=bool(row["is_default"]),
        )
