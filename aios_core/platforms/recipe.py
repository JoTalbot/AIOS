"""On-device calibrate-рецепт: готовый сценарий снятия дампов и калибровки.

Onboarding-пакет платформы (whatsapp/viber/tiktok/instagram/...) идёт с
пустыми ``parser_hints`` — они честно не выдумываются, а снимаются с
живого устройства. Этот модуль превращает этот шаг в повторяемую
процедуру: какие экраны открыть, какие UI-дампы снять, каким CLI их
скормить обратно в ``platforms calibrate --write`` и как закрепить
результат regression-проверкой маркеров.

Ничего не выполняется само: функция возвращает план (шаги списком),
устройство трогает только оператор. Guarded-принцип сохраняется: даже
после калибровки отправка сообщений идёт через outbox.
"""

from __future__ import annotations

# Экраны, которые нужно снять для каждой секции hints.
_SCREENS: dict[str, dict[str, str]] = {
    "cards": {
        "dump": "cards.xml",
        "hint": (
            "откройте ленту/результаты поиска платформы (список карточек), "
            "прокрутите 1-2 экрана, чтобы появились типовые элементы"
        ),
        "cli_flag": "--dump",
    },
    "detail": {
        "dump": "detail.xml",
        "hint": (
            "откройте любую карточку (экран деталей: цена/продавец/CTA-"
            "кнопки), дождитесь полной загрузки"
        ),
        "cli_flag": "--detail",
    },
    "messenger": {
        "dump": "messenger.xml",
        "hint": (
            "откройте инбокс/чат: должны быть видны входящие сообщения, "
            "поле ввода и кнопка отправки"
        ),
        "cli_flag": "--messages",
    },
    "navigation": {
        "dump": "navigation.xml",
        "hint": (
            "вернитесь на главный экран приложения (tab-bar с иконками "
            "ленты/reels/профиля)"
        ),
        "cli_flag": "--navigation",
    },
}

_KIND_HINTS = {
    "messenger": ["messenger"],
    "collector": ["cards"],
    "marketplace": ["cards", "detail", "messenger"],
    "ecommerce": ["cards", "detail", "messenger", "navigation"],
}

_ALL_SECTIONS = ("cards", "detail", "messenger", "navigation")


def _has_hints(hints: dict[str, object], section: str) -> bool:
    value = hints.get(section)
    if not value:
        return False
    if isinstance(value, dict):
        return any(value.values())
    return bool(value)


def calibration_recipe(
    platform: str,
    package: str,
    *,
    kind: str = "marketplace",
    have_hints: dict[str, object] | None = None,
    serial: str | None = None,
    directory: str = "platforms",
) -> dict[str, object]:
    """Строит пошаговый on-device calibrate-рецепт для платформы.

    Args:
        platform: имя платформы (как в ``platforms/<name>.yaml``).
        package: android-пакет (для adb-команд).
        kind: профиль платформы: ``messenger`` (инбокс-first),
            ``collector`` (лента/видео) или ``marketplace`` (полный стек).
        have_hints: текущие ``extras.parser_hints`` дескриптора —
            уже закрытые секции помечаются ``already_have`` и не
            требуют повторного снятия.
        serial: ADB serial устройства, иначе команды без ``-s``.
        directory: каталог дампов/дескрипторов (обычно ``platforms``).

    Returns:
        {platform, package, kind, ready (bool), missing, steps, note}.
        ``steps`` — список {action, title, command?} в порядке выполнения.
    """
    if kind not in _KIND_HINTS:
        raise ValueError(
            f"unknown platform kind '{kind}': expected one of {sorted(_KIND_HINTS)}"
        )
    have_hints = have_hints or {}
    needed: list[str] = list(_KIND_HINTS[kind])
    if kind != "messenger":
        # tab-bar навигация (reels_tab) есть только у ленточных платформ
        needed.append("navigation")
    missing = [section for section in needed if not _has_hints(have_hints, section)]

    serial_part = f"-s {serial} " if serial else ""
    steps: list[dict[str, str]] = [
        {
            "action": "preflight",
            "title": "Подключить устройство и убедиться, что пакет установлен",
            "command": f"adb {serial_part}shell pm path {package}",
        }
    ]

    dump_flags: list[str] = []
    for section in _ALL_SECTIONS:
        if section not in missing:
            continue
        screen = _SCREENS[section]
        dump_path = f"{directory}/{platform}-{screen['dump']}"
        steps.append(
            {
                "action": f"open_{section}",
                "title": screen["hint"],
            }
        )
        steps.append(
            {
                "action": f"dump_{section}",
                "title": f"Снять UI-дамп экрана '{section}'",
                "command": (
                    f"adb {serial_part}shell uiautomator dump "
                    f"/sdcard/{platform}-{section}.xml && "
                    f"adb {serial_part}pull "
                    f"/sdcard/{platform}-{section}.xml {dump_path}"
                ),
            }
        )
        dump_flags.append(f"{screen['cli_flag']} {dump_path}")

    if dump_flags:
        steps.append(
            {
                "action": "calibrate",
                "title": "Извлечь маркеры из дампов и записать в дескриптор",
                "command": (
                    f"aios platforms calibrate --platform {platform} "
                    + " ".join(dump_flags)
                    + " --write"
                ),
            }
        )
        steps.append(
            {
                "action": "verify",
                "title": "Зафиксировать регрессию маркеров (baseline для drift)",
                "command": (
                    f"aios platforms marker-check --platform {platform} "
                    f"--dump {directory}/{platform}-cards.xml"
                    if "cards" in missing
                    else f"aios platforms doctor --platform {platform}"
                ),
            }
        )

    steps.append(
        {
            "action": "doctor",
            "title": "Финальная проверка готовности платформы",
            "command": f"aios platforms doctor --platform {platform}",
        }
    )

    return {
        "platform": platform,
        "package": package,
        "kind": kind,
        "ready": not missing,
        "missing": missing,
        "steps": steps,
        "note": (
            "hints не выдумываются — только с живого устройства; "
            "отправка сообщений остаётся guarded (outbox) даже после "
            "калибровки"
        ),
    }
