"""Generic doctor-отчёт готовности платформы (без платформенного кода).

Чек-лист: adb-бинарь, YAML-дескриптор, секции hints (по требуемым),
хранилище (пересоздаётся read-write), опционально serial в
``adb devices`` и пакет на устройстве. Секреты отчитываются только как
факт наличия env-переменной — значения никогда.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml

from aios_core.platforms.secrets import secret


def platform_doctor(
    platform: str,
    package: str,
    adb=None,
    serial: Optional[str] = None,
    directory: str = "platforms",
    which=None,
    required_hints: Sequence[str] = (),
    secret_fields: Sequence[str] = (),
    storage_factory=None,
) -> Dict[str, object]:
    """Собирает {ok, checks{name:{ok,detail}}} для платформы.

    Args:
        platform: имя платформы (yaml/secrets namespace).
        package: android-пакет (pm path проверка при serial).
        adb: ADBController-like (только для device-проверок).
        serial: ожидаемый в ``adb devices`` serial.
        required_hints: секции parser_hints, которые обязаны быть
            непустыми (например, ("messenger",)).
        secret_fields: env-поля, наличие которых проверяется.
        storage_factory: callable()->storage с .close(), иначе пропуск.
    """
    which = which or shutil.which
    checks: Dict[str, Dict[str, object]] = {}

    adb_bin = which("adb")
    checks["adb_binary"] = {
        "ok": bool(adb_bin),
        "detail": adb_bin or "install Android SDK platform-tools",
    }

    yaml_path = Path(directory) / f"{platform}.yaml"
    doc = {}
    if yaml_path.exists():
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    checks["descriptor"] = {
        "ok": bool(doc and doc.get("name") == platform),
        "detail": str(yaml_path) if yaml_path.exists()
        else f"descriptor not found: {yaml_path}",
    }
    hints = (doc.get("extras") or {}).get("parser_hints") or {}
    for section in required_hints:
        found = bool(hints.get(section))
        checks[f"hints_{section}"] = {
            "ok": found,
            "detail": (
                f"parser_hints.{section} откалиброван" if found
                else f"нет parser_hints.{section} — "
                     f"calibrate --write / onboarding"
            ),
        }
    for field in secret_fields:
        present = bool(secret(platform, field))
        checks[f"secrets_{field.lower()}"] = {
            "ok": present,
            "detail": (
                "env set (value hidden)" if present
                else f"set AIOS_SECRET__{platform.upper()}__{field}"
            ),
        }
    if storage_factory is not None:
        try:
            storage = storage_factory()
            storage.close()
            checks["storage"] = {"ok": True, "detail": "opens,clean"}
        except Exception as exc:  # noqa: BLE001 — честный диагноз
            checks["storage"] = {"ok": False, "detail": str(exc)[:200]}
    if serial and adb is not None:
        devices = adb.run(f"{adb.adb} devices")
        online = f"{serial}\tdevice" in (devices.get("stdout") or "")
        checks["device"] = {
            "ok": bool(devices.get("code") == 0 and online),
            "detail": (
                f"{serial} online" if online
                else f"{serial} не в 'adb devices' (эмулятор запущен?)"
            ),
        }
        if online:
            pm = adb.run(f"{adb.adb} shell pm path {package}")
            checks["package"] = {
                "ok": bool((pm.get("stdout") or "").startswith("package:")),
                "detail": (
                    pm.get("stdout", "").strip()[:120] or
                    f"{package} не установлен — platforms fetch-apk {package}"
                ),
            }
    ok = all(check["ok"] for check in checks.values())
    return {"platform": platform, "ok": ok, "checks": checks}
