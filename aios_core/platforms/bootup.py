"""Bootup — E2E-пайплайн подключения новой платформы «из APK до коллектора».

Одна команда ``aios platforms bootup`` выполняет всю цепь дорожной карты
10000+:

1. **scaffold** — скелет платформы из APK (``aapt dump badging`` → spec)
   или из пары ``--name/--package``; повторный запуск продолжает
   (resume) с уже существующего скелета;
2. **register** — YAML-дескриптор регистрируется в реестре платформ;
3. **calibrate** — источник UI-дампа поисковой выдачи: ``--dump файл``
   → инъецированный ``driver(package, query)`` → дефолтный generic-драйв
   по ADB (открыть приложение, подождать, снять дамп текущего экрана);
   CalibrationAdvisor вытаскивает parser_hints;
4. **hints → descriptor** — подсказки пишутся в ``extras.parser_hints``
   YAML-дескриптора, дескриптор перерегистрируется;
5. **codegen** — parsergen компилирует ``card_parser.py`` модуля из
   маркеров;
6. **verify** — дамп разбирается свежим парсером; статус ``ready``,
   если найдена хотя бы одна карточка.

Итог — структурированный отчёт по шагам. ``dry_run=True`` гарантирует
нулевые записи на диск: все шаги возвращают планы.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from .calibrate import CalibrationAdvisor, write_hints_to_descriptor
from .catalog import load_catalog_file
from .parsergen import build_parser, extract_markers, write_parser
from .scaffold import scaffold_from_apk, scaffold_platform

#: Сигнатура инъецируемого калибровочного драйва:
#: driver(android_package, query) -> XML-текст дампа поисковой выдачи.
Driver = Callable[[str, Optional[str]], str]


def _adb_calibrator_drive(package: str, query: Optional[str] = None) -> str:
    """Generic-драйв по ADB: открыть приложение → пауза → дамп экрана.

    Эвристика: большинство маркетплейс-приложений открываются лентой
    объявлений, её дампа достаточно калибровщику. Точечный драйв под
    конкретный экран поиска — задача профильного агента платформы.
    """
    from aios_core.modules.olx.adb import ADBController

    adb = ADBController(package=package)
    opened = adb.open_app()
    if opened.get("code") != 0:
        raise ValueError(
            f"adb open_app failed: {(opened.get('stderr') or 'no device')[:160]}"
        )
    time.sleep(8)  # приложению нужно прогрузить ленту
    with tempfile.TemporaryDirectory(prefix="aios-bootup-") as tmp:
        target = Path(tmp) / "screen.xml"
        pulled = adb.dump_ui(str(target))
        if pulled.get("code") != 0 or not target.exists():
            raise ValueError(
                "adb dump_ui failed: "
                f"{(pulled.get('stderr') or 'dump unavailable')[:160]}"
            )
        return target.read_text(encoding="utf-8")


def bootup_platform(
    apk_path: Optional[str] = None,
    *,
    name: Optional[str] = None,
    package: Optional[str] = None,
    project_root=".",
    locale: str = "uk-UA",
    dump_path: Optional[str] = None,
    query: Optional[str] = None,
    driver: Optional[Driver] = None,
    runner=None,
    dry_run: bool = False,
) -> Dict[str, object]:
    """E2E-пайплайн подключения платформы.

    Args:
        apk_path: Путь к APK (inspect через aapt). Если не задан —
            обязательны ``name`` и ``package``.
        name: Имя платформы (переопределяет guess из APK).
        package: Android-пакет (без APK).
        project_root: Корень репозитория.
        locale: Локаль дескриптора.
        dump_path: Готовый UI-дамп выдачи (обходит драйв).
        query: Поисковый запрос для live-драйва (контекст отчёта).
        driver: Инъекция калибровочного драйва ``(package, query)->xml``.
        runner: Инъекция ``aapt dump badging`` runner'а (тесты).
        dry_run: Без записей на диск — только планы шагов.

    Returns:
        {platform, android_package, status, dry_run, steps: {...}}.

    Raises:
        ValueError: Нет ни APK, ни пары name/package; невалидные входные.
    """
    if not apk_path and not (name and package):
        raise ValueError(
            "bootup needs either --apk or both --name and --package"
        )

    root = Path(project_root)
    steps: Dict[str, object] = {}

    # -- 1. scaffold ----------------------------------------------------- #
    scaffold_files: Dict[str, str] = {}
    scaffold_mode = "planned" if dry_run else "written"
    try:
        if apk_path:
            result = scaffold_from_apk(
                apk_path, name=name, project_root=root,
                locale=locale, dry_run=dry_run, runner=runner,
            )
            spec = result["spec"]
            scaffold_files = result["files"]
            platform_name = name or spec["candidate_name"]
            android_package = spec["android_package"]
            steps["scaffold"] = {
                "mode": scaffold_mode,
                "spec": spec,
                "files": sorted(scaffold_files),
            }
        else:
            scaffold_files = scaffold_platform(
                name, package, project_root=root,
                locale=locale, dry_run=dry_run,
            )
            platform_name = name
            android_package = package
            steps["scaffold"] = {
                "mode": scaffold_mode,
                "files": sorted(scaffold_files),
            }
    except ValueError as exc:
        if "file already exists" not in str(exc):
            raise
        # resume: скелет уже есть — продолжаем с дескриптора на диске
        if not (name or apk_path):
            raise
        if apk_path:
            from .scaffold import inspect_apk
            spec = inspect_apk(apk_path, runner=runner)
            platform_name = name or spec["candidate_name"]
            android_package = spec["android_package"]
        else:
            platform_name, android_package = name, package
        steps["scaffold"] = {"mode": "resumed",
                             "note": str(exc).split(":")[0]}

    yaml_path = root / "platforms" / f"{platform_name}.yaml"

    # -- 2. register ----------------------------------------------------- #
    if dry_run:
        steps["register"] = {"mode": "skipped", "reason": "dry-run"}
    else:
        loaded = load_catalog_file(yaml_path)
        steps["register"] = {
            "mode": "registered",
            "platform": loaded[0].name,
            "extras_keys": sorted(loaded[0].extras),
        }

    # -- 3. calibrate ---------------------------------------------------- #
    xml: Optional[str] = None
    hints: Optional[Dict[str, object]] = None
    calibrate_step: Dict[str, object] = {}
    if dump_path:
        xml = Path(dump_path).read_text(encoding="utf-8")
        calibrate_step["source"] = f"dump:{dump_path}"
    else:
        drive = driver or _adb_calibrator_drive
        try:
            xml = drive(android_package, query)
            calibrate_step["source"] = (
                "driver:injected" if driver else "driver:adb-generic"
            )
        except Exception as exc:  # noqa: BLE001 — драйв опционален
            calibrate_step.update({
                "source": "driver:adb-generic",
                "mode": "skipped",
                "reason": str(exc)[:200],
            })
    if xml:
        hints = CalibrationAdvisor().analyze(xml)
        calibrate_step["hints"] = hints
    steps["calibrate"] = calibrate_step

    markers = extract_markers(hints or {})

    # -- 4. hints → descriptor ------------------------------------------- #
    if hints and markers:
        if dry_run:
            steps["hints"] = {"mode": "planned", "target": str(yaml_path)}
        else:
            written = write_hints_to_descriptor(
                platform_name, hints, directory=root / "platforms",
            )
            reloaded = load_catalog_file(yaml_path)
            steps["hints"] = {
                "mode": "written",
                "target": written,
                "registered_extras": sorted(reloaded[0].extras),
            }
    else:
        steps["hints"] = {"mode": "skipped", "reason": "no card markers"}

    # -- 5. codegen ------------------------------------------------------- #
    if markers and platform_name:
        try:
            codegen_files = write_parser(
                platform_name, hints, project_root=root,
                android_package=android_package,
                dry_run=dry_run, overwrite=True,
            )
            steps["codegen"] = {
                "mode": "planned" if dry_run else "written",
                "files": sorted(codegen_files),
                "markers": list(markers),
            }
        except ValueError as exc:
            steps["codegen"] = {"mode": "skipped", "reason": str(exc)}
    else:
        steps["codegen"] = {"mode": "skipped", "reason": "no card markers"}

    # -- 6. verify --------------------------------------------------------- #
    cards = []
    if xml and markers:
        cards = build_parser(hints).parse(xml, query=query)
        steps["verify"] = {
            "cards": len(cards),
            "sample_titles": [c.title for c in cards[:3]],
        }
    else:
        steps["verify"] = {"mode": "skipped", "reason": "no calibration data"}

    if cards:
        status = "ready"
    elif xml and hints is not None:
        status = "calibration-empty"
    else:
        status = "scaffolded"

    return {
        "platform": platform_name,
        "android_package": android_package,
        "status": status,
        "dry_run": dry_run,
        "steps": steps,
    }
