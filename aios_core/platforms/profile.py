"""Profile — один аккаунт одной платформы.

Профиль связывает логический аккаунт (``olx:work``) с физическими
ресурсами: устройством/эмулятором (ADB serial), отдельным файлом
хранилища, локалью и Android user-id. Изоляция по хранилищу
(``data/<platform>/<profile>.sqlite``) гарантирует, что данные разных
аккаунтов не смешиваются и масштабируются независимо.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class Profile:
    """Аккаунт платформы.

    Attributes:
        platform: Имя платформы (``"olx"``).
        name: Имя профиля внутри платформы (``"work"``).
        device_serial: ADB serial устройства/эмулятора, закреплённого за
            профилем (``None`` — устройство по умолчанию).
        android_user: Android user/profile id (для multi-user на одном
            устройстве), 0 = основной пользователь.
        db_path: Путь к SQLite-хранилищу профиля.
        locale: Локаль приложения.
        notes: Произвольные пометки.
        is_default: Профиль по умолчанию для платформы.
        ephemeral: Профиль синтезирован резолвером (не из реестра).
    """

    platform: str
    name: str
    device_serial: str | None = None
    android_user: int = 0
    db_path: str | None = None
    locale: str = "uk-UA"
    notes: str = ""
    is_default: bool = False
    ephemeral: bool = False

    @property
    def key(self) -> str:
        """Полный ключ профиля: ``platform:name``."""
        return f"{self.platform}:{self.name}"

    @property
    def fingerprint(self) -> str:
        """Стабильный короткий идентификатор профиля."""
        base = f"profile:{self.key}".lower()
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict[str, object]:
        """JSON-представление профиля."""
        return {
            "platform": self.platform,
            "name": self.name,
            "key": self.key,
            "fingerprint": self.fingerprint,
            "device_serial": self.device_serial,
            "android_user": self.android_user,
            "db_path": self.db_path,
            "locale": self.locale,
            "notes": self.notes,
            "is_default": self.is_default,
            "ephemeral": self.ephemeral,
        }
