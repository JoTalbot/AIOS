"""AIOS Platforms — масштабируемый реестр маркетплейс-приложений и профилей.

Архитектура «платформа → профили» рассчитана на тысячи приложений,
аналогичных OLX: каждое приложение описывается дескриптором
(:class:`PlatformDescriptor`), каждый аккаунт — профилем
(:class:`Profile`) со своим устройством (ADB serial) и своим хранилищем
(``data/<platform>/<profile>.sqlite``).

CLI и REST API разрешают контекст работы через единый резолвер:
явный выбор → переменная окружения ``AIOS_PROFILE`` → профиль по умолчанию
платформы → встроенный эфемерный ``default``.
"""

from .catalog import load_catalog, load_catalog_file
from .descriptor import (
    PlatformDescriptor,
    get_platform,
    list_platforms,
    register_platform,
)
from .devices import DevicePool
from .fleet import PoolMonitor, ensure_device
from .profile import Profile
from .resolver import (
    adb_for,
    resolve_profile,
    storage_for,
)
from .scaffold import inspect_apk, scaffold_from_apk, scaffold_platform
from .shards import ShardRouter
from .store import ProfileStore

__all__ = [
    "DevicePool",
    "PlatformDescriptor",
    "PoolMonitor",
    "Profile",
    "ProfileStore",
    "ShardRouter",
    "adb_for",
    "ensure_device",
    "get_platform",
    "inspect_apk",
    "list_platforms",
    "load_catalog",
    "load_catalog_file",
    "register_platform",
    "resolve_profile",
    "scaffold_from_apk",
    "scaffold_platform",
    "storage_for",
]
