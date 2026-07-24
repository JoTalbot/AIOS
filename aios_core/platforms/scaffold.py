"""Scaffold — генератор скелета новой платформы из дескриптора.

Шаг кодогенерации из дорожной карты 10000+: одна команда создаёт

* ``platforms/<name>.yaml`` — дескриптор каталога;
* ``aios_core/modules/<name>/__init__.py`` — модуль агента;
* ``aios_core/modules/<name>/storage.py`` — хранилище, наследующее
  проверенную схему/поведение OLXStorage (история цен, аутбокс,
  свои объявления и т.д. доступны сразу);
* ``tests/test_<name>_agent.py`` — дымовой тест модуля.

ADB-контроллер переиспользуется (``adb_class`` указывает на общий
``ADBController``) — командная инфраструктура общая, платформа отличается
только пакетом в дескрипторе.
"""

from __future__ import annotations

import re
from pathlib import Path

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
_PACKAGE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")
_ADB_CLASS = "aios_core.modules.olx.adb.ADBController"

_YAML_TEMPLATE = """# Сгенерировано aios platforms scaffold ({name})
name: {name}
android_package: {android_package}
agent_module: aios_core.modules.{module_name}
storage_class: aios_core.modules.{module_name}.storage.{class_name}Storage
adb_class: {adb_class}
default_locale: {locale}
description: {description_yaml}
legacy_default_db: {name}_default.sqlite
extras:
  compliance:
    autopost_allowed: false
    messenger: approval-only
    collector: false
    note: "deny-by-default: задекларируйте ToS-политику площадки при onboarding"
  parser_hints: {{}}
"""


def _yaml_double_quoted(value: str) -> str:
    """Безопасный YAML-скаляр в двойных кавычках (двоеточия/апострофы)."""
    escaped = (value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


_INIT_TEMPLATE = '''"""{title} marketplace agent — скелет, сгенерированный scaffold.

Хранилище унаследовано от OLXStorage: схема объявлений, история цен,
подписки/избранное, outbox, свои объявления, конкурентные связи, kv-профиль.
Парсеры/коллекторы платформы добавляются сюда по мере калибровки под
её приложение ({android_package}).
"""

from .storage import {class_name}Storage

__all__ = ["{class_name}Storage"]
'''

_STORAGE_TEMPLATE = '''"""{title} storage — наследник OLXStorage с общей схемой объявлений."""

from aios_core.modules.olx.storage import OLXStorage


class {class_name}Storage(OLXStorage):
    """Хранилище платформы {name}: общая схема ads/price-history/outbox/...."""

    pass
'''

_TEST_TEMPLATE = '''"""Smoke-тесты сгенерированного модуля платформы {name}."""

from aios_core.platforms import get_platform
from aios_core.modules.{module_name} import {class_name}Storage


def test_{safe_name}_storage_opens_and_counts():
    storage = {class_name}Storage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_{safe_name}_platform_registered():
    descriptor = get_platform("{name}")
    assert descriptor.android_package == "{android_package}"
'''


# --------------------------------------------------------------------------- #
# APK inspection (aapt dump badging → черновой дескриптор)                     #
# --------------------------------------------------------------------------- #

_PKG_BADGE_RE = re.compile(r"package: name='(?P<pkg>[^']+)'")
_LABEL_RE = re.compile(r"application-label:'(?P<label>[^']*)'")
_LAUNCH_RE = re.compile(r"launchable-activity: name='(?P<activity>[^']+)'")
_SDK_RE = re.compile(r"targetSdkVersion:'(?P<target_sdk>[^']+)'")


def _badging(apk_path: str) -> dict[str, str]:
    """Реальный вызов aapt dump badging (требует Android SDK cmdline-tools)."""
    import subprocess

    result = subprocess.run(
        f"aapt dump badging '{apk_path}'",
        shell=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def inspect_apk(apk_path: str, runner=None) -> dict[str, str | None]:
    """Черновой дескриптор платформы из APK.

    Читает `aapt dump badging`: android-пакет, метку приложения,
    launchable-activity, target SDK. ``runner`` инъецируется для тестов.

    Returns:
        {android_package, candidate_name, app_label, launchable_activity,
         target_sdk} — candidate_name = последний сегмент пакета.

    Raises:
        ValueError: APK не читается (aapt недоступен / битый файл).
    """
    runner = runner or _badging
    if not str(apk_path).endswith(".apk"):
        raise ValueError(f"not an .apk file: {apk_path}")
    result = runner(str(apk_path))
    if result.get("code") != 0:
        raise ValueError(
            "aapt dump badging failed (Android SDK cmdline-tools required): "
            f"{(result.get('stderr') or '').strip()[:200]}"
        )
    stdout = result.get("stdout") or ""
    package = _PKG_BADGE_RE.search(stdout)
    if not package:
        raise ValueError(f"could not read package name from {apk_path}")
    android_package = package.group("pkg")
    label = _LABEL_RE.search(stdout)
    launch = _LAUNCH_RE.search(stdout)
    sdk = _SDK_RE.search(stdout)
    candidate = re.sub(
        r"[^a-z0-9]+", "-", android_package.split(".")[-1].lower()
    ).strip("-")
    return {
        "android_package": android_package,
        "candidate_name": candidate,
        "app_label": label.group(1) if label else None,
        "launchable_activity": launch.group(1) if launch else None,
        "target_sdk": sdk.group(1) if sdk else None,
    }


def scaffold_from_apk(
    apk_path: str,
    name: str | None = None,
    project_root=".",
    locale: str = "uk-UA",
    dry_run: bool = False,
    runner=None,
) -> dict[str, object]:
    """Авто-scaffold платформы из APK: inspect → scaffold_platform.

    Returns:
        {"spec": <inspect_apk result>, "files": {path: content}}.
    """
    spec = inspect_apk(apk_path, runner=runner)
    platform_name = name or spec["candidate_name"]
    files = scaffold_platform(
        platform_name,
        spec["android_package"],
        project_root=project_root,
        description=(
            f"{spec.get('app_label') or platform_name} "
            f"(auto-scaffold from {Path(apk_path).name}, "
            f"launchable: {spec.get('launchable_activity') or 'n/a'})"
        ),
        locale=locale,
        dry_run=dry_run,
    )
    return {"spec": spec, "files": files}


def _class_name(platform_name: str) -> str:
    """Имя класса из имени платформы: demo-market → DemoMarket."""
    return "".join(part.capitalize() for part in platform_name.split("-"))


def _module_name(platform_name: str) -> str:
    """Имя python-модуля: demo-market → demo_market."""
    return platform_name.replace("-", "_")


def scaffold_platform(
    name: str,
    android_package: str,
    project_root=".",
    description: str = "",
    locale: str = "uk-UA",
    dry_run: bool = False,
) -> dict[str, str]:
    """Генерирует скелет платформы.

    Args:
        name: Имя платформы (``^[a-z][a-z0-9-]{1,30}$``).
        android_package: Android-пакет приложения.
        project_root: Корень репозитория.
        description: Описание для дескриптора.
        locale: Локаль по умолчанию.
        dry_run: Только вернуть план {path: content}, не записывая.

    Returns:
        Словарь ``{путь: содержимое}`` записанных/планируемых файлов.

    Raises:
        ValueError: Невалидные входные данные или файлы уже существуют.
    """
    if not _NAME_RE.match(name or ""):
        raise ValueError(
            f"invalid platform name '{name}' (use lowercase, digits, dashes)"
        )
    if not _PACKAGE_RE.match(android_package or ""):
        raise ValueError(f"invalid android package '{android_package}'")

    root = Path(project_root)
    module_name = _module_name(name)
    class_name = _class_name(name)
    title = name.replace("-", " ").title()

    files = {
        str(root / "platforms" / f"{name}.yaml"): _YAML_TEMPLATE.format(
            name=name,
            android_package=android_package,
            module_name=module_name,
            class_name=class_name,
            adb_class=_ADB_CLASS,
            locale=locale,
            description_yaml=_yaml_double_quoted(
                description or f"{title} marketplace agent"
            ),
        ),
        str(
            root / "aios_core" / "modules" / module_name / "__init__.py"
        ): _INIT_TEMPLATE.format(
            title=title,
            name=name,
            module_name=module_name,
            class_name=class_name,
            android_package=android_package,
        ),
        str(
            root / "aios_core" / "modules" / module_name / "storage.py"
        ): _STORAGE_TEMPLATE.format(
            title=title,
            name=name,
            class_name=class_name,
        ),
        str(root / "tests" / f"test_{module_name}_agent.py"): _TEST_TEMPLATE.format(
            name=name,
            safe_name=module_name,
            module_name=module_name,
            class_name=class_name,
            android_package=android_package,
        ),
    }

    for path in files:
        if Path(path).exists():
            raise ValueError(f"file already exists: {path}")

    if not dry_run:
        for path, content in files.items():
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    return files
