"""YAML-каталог платформ — реестр как данные.

Шаг к 10000+ приложений: платформа регистрируется из файла, без кода.
Каталог — каталог (по умолчанию ``platforms/``) с ``*.yaml``-файлами:

.. code-block:: yaml

    name: olx                       # обязателен
    android_package: ua.slando      # обязателен
    agent_module: aios_core.modules.olx
    storage_class: aios_core.modules.olx.storage.OLXStorage
    adb_class: aios_core.modules.olx.adb.ADBController
    default_locale: uk-UA
    description: Slando Ukraine agent
    legacy_default_db: olx_ads.sqlite

``storage_class``/``adb_class`` — dotted-пути классов; фабрики строятся
по контракту ``Storage(db_path)`` и ``ADB(package=..., serial=...)``.
Файлы читаются в отсортированном порядке; повторная регистрация имени
переопределяет дескриптор.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

from .descriptor import PlatformDescriptor, register_platform

_REQUIRED_FIELDS = ("name", "android_package")


def _import_class(dotted: str):
    """Импортирует класс по dotted-пути."""
    module_name, _, attr = dotted.rpartition(".")
    if not module_name:
        raise ValueError(f"malformed class path '{dotted}'")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _descriptor_from_spec(spec: Dict, source: str) -> PlatformDescriptor:
    """Строит дескриптор из YAML-спеки."""
    for field in _REQUIRED_FIELDS:
        if not spec.get(field):
            raise ValueError(f"{source}: required field '{field}' is missing")

    storage_factory = None
    if spec.get("storage_class"):
        storage_cls = _import_class(spec["storage_class"])
        storage_factory = lambda db_path, _cls=storage_cls: _cls(db_path)

    adb_factory = None
    if spec.get("adb_class"):
        adb_cls = _import_class(spec["adb_class"])
        adb_factory = lambda package, serial=None, _cls=adb_cls: _cls(
            package=package, serial=serial
        )

    return PlatformDescriptor(
        name=spec["name"],
        android_package=spec["android_package"],
        agent_module=spec.get("agent_module") or f"aios_core.modules.{spec['name']}",
        storage_factory=storage_factory,
        adb_factory=adb_factory,
        default_locale=spec.get("default_locale") or "uk-UA",
        description=spec.get("description") or "",
        legacy_default_db=spec.get("legacy_default_db"),
        extras=spec.get("extras") or {},
    )


def load_catalog_file(path: Union[str, Path]) -> List[PlatformDescriptor]:
    """Регистрирует платформы из одного YAML-файла.

    Файл содержит либо одну спеку, либо словарь с ключом ``platforms``
    (список спек). Возвращает зарегистрированные дескрипторы.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, (dict, list)):
        raise ValueError(f"{path}: catalog file must contain a mapping or a list")
    if isinstance(data, dict) and "platforms" in data:
        specs = data["platforms"]
    elif isinstance(data, list):
        specs = data
    else:
        specs = [data]
    loaded = []
    for spec in specs:
        descriptor = _descriptor_from_spec(spec, source=str(path))
        register_platform(descriptor)
        loaded.append(descriptor)
    return loaded


def load_catalog(
    directory: Union[str, Path] = "platforms",
) -> List[PlatformDescriptor]:
    """Регистрирует все платформы каталога (``*.yaml``/``*.yml``, sorted)."""
    directory = Path(directory)
    loaded: List[PlatformDescriptor] = []
    if not directory.is_dir():
        return loaded
    for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        loaded.extend(load_catalog_file(path))
    return loaded
