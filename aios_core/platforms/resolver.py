"""Resolver — единая точка разрешения контекста «платформа + профиль».

Приоритет выбора профиля (одинаков для CLI и REST API):

1. явное имя (``--profile`` / ``?profile=``);
2. переменная окружения ``AIOS_PROFILE``;
3. профиль по умолчанию платформы из реестра;
4. встроенный эфемерный ``default`` (обратная совместимость: ровно
   прежнее поведение однопрофильной установки).
"""

from __future__ import annotations

import os
from typing import Optional

from .descriptor import get_platform
from .profile import Profile
from .store import ProfileStore


def _default_db_path(platform: str) -> str:
    """Путь БД эфемерного default-профиля (legacy-совместимость)."""
    descriptor = get_platform(platform)
    if descriptor.legacy_default_db:
        return descriptor.legacy_default_db
    return f"{platform}_default.sqlite"


def resolve_profile(
    platform: str,
    name: Optional[str] = None,
    store: Optional[ProfileStore] = None,
) -> Profile:
    """Разрешает профиль платформы по описанному приоритету.

    Args:
        platform: Имя платформы (должна быть зарегистрирована).
        name: Явное имя профиля или None.
        store: Реестр профилей; по умолчанию — синглтон
            :meth:`ProfileStore.default`.

    Returns:
        Найденный или синтезированный :class:`Profile`.

    Raises:
        ValueError: Платформа неизвестна или запрошенный профиль не найден.
    """
    descriptor = get_platform(platform)
    store = store or ProfileStore.default()

    if not name:
        name = os.environ.get("AIOS_PROFILE") or None

    if name:
        profile = store.get(platform, name)
        if profile is None:
            raise ValueError(
                f"profile '{platform}:{name}' not found in registry"
            )
        return _with_db_path(profile, descriptor)

    default = store.get_default(platform)
    if default is not None:
        return _with_db_path(default, descriptor)

    return Profile(
        platform=platform,
        name="default",
        db_path=_default_db_path(platform),
        locale=descriptor.default_locale,
        ephemeral=True,
    )


def _with_db_path(profile: Profile, descriptor) -> Profile:
    """Подставляет дефолтный путь БД, если у профиля он не задан."""
    if not profile.db_path:
        profile.db_path = os.path.join(
            "data", descriptor.name, f"{profile.name}.sqlite"
        )
    return profile


def storage_for(
    platform: str,
    name: Optional[str] = None,
    store: Optional[ProfileStore] = None,
):
    """Хранилище платформы для разрешённого профиля."""
    descriptor = get_platform(platform)
    profile = resolve_profile(platform, name, store)
    return descriptor.make_storage(profile.db_path)


def adb_for(
    platform: str,
    name: Optional[str] = None,
    store: Optional[ProfileStore] = None,
):
    """ADB-контроллер платформы, привязанный к устройству профиля."""
    descriptor = get_platform(platform)
    profile = resolve_profile(platform, name, store)
    return descriptor.make_adb(profile.device_serial)
