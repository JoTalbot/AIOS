"""Onboarding wizard: «подключить приложение» одной командой.

Цепочка: resolve/fetch APK → bootup (scaffold→register→calibrate→
hints→codegen→verify) → паспорт готовности. Каждый шаг честный:
чего не хватило (устройства/дампа/калибровки) — получаете явный
next_commands, а не silently-заглушку.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from aios_core.platforms.bootup import bootup_platform


def onboard_package(
    apk: Optional[str] = None,
    name: Optional[str] = None,
    package: Optional[str] = None,
    project_root: str = ".",
    fetch: bool = False,
    apks_dir: str = "apks",
    dump_path: Optional[str] = None,
    query: Optional[str] = None,
    serial: Optional[str] = None,
    pool=None,
    driver: Optional[Callable] = None,
    runner=None,
    apk_runner=None,
    dry_run: bool = False,
) -> Dict[str, object]:
    """Единый вход подключения платформы.

    Args:
        apk: путь к APK или android-пакет (с ``fetch=True``).
        name/package: явное имя платформы/пакета.
        fetch: скачать APK через apkeep, если это пакет без файла.
        dump_path: свежий search-дамп (калибровка); None → driver/pool
            или честный статус «needs device».
        driver: callable(package, query, serial) -> xml (удалённый
            дамп-драйв); pool: DevicePool для lease.

    Returns:
        {platform, package, status, bootup(report), passport(checks),
         next_commands}: passport — {scaffolded, registered,
         hints_card_markers, parser_codegen, verified_cards}.
    """
    report = bootup_platform(
        apk_path=apk,
        name=name,
        package=package,
        project_root=project_root,
        fetch=fetch,
        apks_dir=apks_dir,
        dump_path=dump_path,
        query=query,
        serial=serial,
        pool=pool,
        driver=driver,
        runner=runner,
        apk_runner=apk_runner,
        dry_run=dry_run,
    )
    platform = report["platform"]
    steps = report.get("steps") or {}
    calibrate = steps.get("calibrate") or {}
    codegen = steps.get("codegen") or {}
    verify = steps.get("verify") or {}
    hints = calibrate.get("hints") or {}
    passport = {
        "scaffolded": bool(steps.get("scaffold")),
        "registered": platform is not None,
        "hints_card_markers": len(hints.get("card_markers") or []),
        "parser_codegen": bool(codegen.get("parser")),
        "verified_cards": int(verify.get("cards") or 0),
    }
    next_commands: List[str] = []
    if report.get("status") != "ready":
        if not dump_path and driver is None:
            next_commands.append(
                "# калибровка: получить search-дамп с устройства и "
                "повторить: aios onboard {apk} --dump dump.xml"
            )
        next_commands.append(f"aios platforms doctor --platform {platform or '<name>'}")
    else:
        next_commands.extend(
            [
                f"aios platforms autowatch --platform {platform} --once",
                f"aios platforms doctor --platform {platform}",
            ]
        )
    return {
        "platform": platform,
        "package": report.get("android_package"),
        "status": report.get("status"),
        "bootup": report,
        "passport": passport,
        "next_commands": next_commands,
    }
