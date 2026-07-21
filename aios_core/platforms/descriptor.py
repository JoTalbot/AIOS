"""Platform descriptors — реестр маркетплейс-приложений.

Дескриптор описывает приложение уровня OLX (Android-пакет, агентский
модуль, фабрику хранилища). Реестр открыт: новые платформы добавляются
через :func:`register_platform` — без изменения существующего кода
(Open/Closed). При 10000+ приложениях дескрипторы подгружаются из
каталога/конфигурации, CLI и REST генерируются из них механически.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class PlatformDescriptor:
    """Описание одного маркетплейс-приложения.

    Attributes:
        name: Короткое уникальное имя платформы (``"olx"``).
        android_package: Имя Android-пакета приложения.
        agent_module: Питон-модуль агента с парсерами/хранилищем.
        storage_factory: Фабрика хранилища: ``storage_factory(db_path)``.
        adb_factory: Фабрика ADB-контроллера: ``adb_factory(serial)``.
        default_locale: Локаль приложения по умолчанию.
        description: Человекочитаемое описание.
        legacy_default_db: Путь БД встроенного профиля ``default``
            (обратная совместимость с однопрофильными установками).
        extras: Свободные расширения дескриптора (например,
            ``parser_hints`` из калибровки).
    """

    name: str
    android_package: str
    agent_module: str
    storage_factory: Optional[Callable] = None
    adb_factory: Optional[Callable] = None
    default_locale: str = "uk-UA"
    description: str = ""
    legacy_default_db: Optional[str] = None
    extras: Dict = field(default_factory=dict)

    def make_storage(self, db_path: str):
        """Создаёт хранилище этой платформы по пути БД."""
        if self.storage_factory is None:
            raise ValueError(f"platform '{self.name}' has no storage factory")
        return self.storage_factory(db_path)

    def make_adb(self, serial: Optional[str] = None):
        """Создаёт ADB-контроллер этой платформы (с device-binding)."""
        if self.adb_factory is None:
            raise ValueError(f"platform '{self.name}' has no adb factory")
        return self.adb_factory(self.android_package, serial)

    def to_dict(self) -> Dict[str, object]:
        """JSON-представление дескриптора."""
        return {
            "name": self.name,
            "android_package": self.android_package,
            "agent_module": self.agent_module,
            "default_locale": self.default_locale,
            "description": self.description,
            "extras": self.extras,
        }


def _olx_storage_factory(db_path: str):
    from aios_core.modules.olx import OLXStorage

    return OLXStorage(db_path)


def _olx_adb_factory(android_package: str, serial: Optional[str] = None):
    from aios_core.modules.olx import ADBController

    return ADBController(package=android_package, serial=serial)


_PLATFORMS: Dict[str, PlatformDescriptor] = {}


def register_platform(descriptor: PlatformDescriptor) -> None:
    """Регистрирует (или заменяет) платформу в реестре."""
    _PLATFORMS[descriptor.name] = descriptor


def get_platform(name: str) -> PlatformDescriptor:
    """Возвращает дескриптор платформы или бросает ``ValueError``."""
    try:
        return _PLATFORMS[name]
    except KeyError:
        known = ", ".join(sorted(_PLATFORMS)) or "<empty>"
        raise ValueError(
            f"unknown platform '{name}' (registered: {known})"
        ) from None


def list_platforms() -> List[PlatformDescriptor]:
    """Все зарегистрированные платформы, по имени."""
    return [_PLATFORMS[name] for name in sorted(_PLATFORMS)]


register_platform(
    PlatformDescriptor(
        name="olx",
        android_package="ua.slando",
        agent_module="aios_core.modules.olx",
        storage_factory=_olx_storage_factory,
        adb_factory=_olx_adb_factory,
        default_locale="uk-UA",
        description="OLX Ukraine Android agent (коллекция, мессенджер, "
                    "свои объявления, конкуренты, советник)",
        legacy_default_db="olx_ads.sqlite",
    )
)
