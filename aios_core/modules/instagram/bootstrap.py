"""Instagram bootstrap — doctor-отчёт готовности платформы.

Проверки (значения секретов никогда не отчитываются — только факт
наличия переменной): adb-бинарь, env-секреты, YAML-дескриптор,
калиброванные маркеры карточек, хранилище, опционально serial в
``adb devices``. Инъекции (which/adapter) держат doctor тестируемым
без устройства.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Optional

from aios_core.platforms.parsergen import build_parser, extract_markers
from aios_core.platforms.runtime_hints import load_hints_section
from aios_core.platforms.secrets import env_name, secret

PLATFORM = "instagram"
PACKAGE = "com.instagram.android"


class InstagramBootstrap:
    """Смотритель готовности Instagram-платформы к сбору/диалогам."""

    def __init__(
        self,
        adb=None,
        serial: Optional[str] = None,
        directory: str = "platforms",
        which=None,
    ):
        self.adb = adb
        self.serial = serial
        self.directory = Path(directory)
        self.which = which or shutil.which

    def doctor(self) -> Dict[str, object]:
        """{ok, checks: {name: {ok, detail}}, hints_status}."""
        checks: Dict[str, Dict[str, object]] = {}

        adb_bin = self.which("adb")
        checks["adb_binary"] = {
            "ok": bool(adb_bin),
            "detail": adb_bin or "install Android SDK platform-tools",
        }

        for field in ("USERNAME", "PASSWORD"):
            present = bool(secret(PLATFORM, field))
            checks[f"secrets_{field.lower()}"] = {
                "ok": present,
                "detail": (
                    "set via env"
                    if present
                    else f"missing: export {env_name(PLATFORM, field)}"
                ),
            }

        yaml_path = self.directory / f"{PLATFORM}.yaml"
        checks["descriptor"] = {
            "ok": yaml_path.exists(),
            "detail": str(yaml_path),
        }

        markers: tuple = ()
        try:
            import yaml

            doc = yaml.safe_load(yaml_path.read_text("utf-8")) or {}
            hints = (doc.get("extras") or {}).get("parser_hints") or {}
            markers = extract_markers(hints)
        except Exception:  # noqa: BLE001 — broken yaml честно помечаем
            hints = {}
        checks["card_markers"] = {
            "ok": bool(markers),
            "detail": (
                f"markers: {', '.join(markers)}"
                if markers
                else "not calibrated: aios platforms bootup "
                "--apk com.instagram.android --fetch"
            ),
        }
        detail_hints = (
            load_hints_section(PLATFORM, "detail", self.directory)
            if yaml_path.exists()
            else {}
        )
        checks["detail_markers"] = {
            "ok": bool(
                detail_hints.get("seller_markers") or detail_hints.get("price_nodes")
            ),
            "detail": "calibrate --detail post.xml --write",
        }

        try:
            from .storage import InstagramStorage

            storage = InstagramStorage(":memory:")
            storage.close()
            storage_ok, storage_detail = True, "schema opens"
        except Exception as exc:  # noqa: BLE001
            storage_ok, storage_detail = False, str(exc)[:120]
        checks["storage"] = {"ok": storage_ok, "detail": storage_detail}

        if self.serial is not None:
            if self.adb is None:
                checks["device"] = {
                    "ok": False,
                    "detail": "adb adapter not injected",
                }
            else:
                devices = self.adb.run(f"{self.adb.adb} devices")
                online = self.serial in (devices.get("stdout") or "")
                checks["device"] = {
                    "ok": online,
                    "detail": (
                        f"{self.serial} online"
                        if online
                        else f"{self.serial} not in adb devices"
                    ),
                }

        required = {k: v for k, v in checks.items() if k != "detail_markers"}
        return {
            "ok": all(check["ok"] for check in required.values()),
            "platform": PLATFORM,
            "android_package": PACKAGE,
            "checks": checks,
        }
