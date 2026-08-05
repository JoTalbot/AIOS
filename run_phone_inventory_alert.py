#!/usr/bin/env python3
"""Alert owner about safe Android inventory drift without app/chat payloads."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from aios_core.phone_inventory import PhoneInventory

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "android_gateway" / "inventory_alert_state.json"


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _send(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30):
        pass
    return True


def check(alert: bool = False, bootstrap: bool = False, inventory_factory=PhoneInventory) -> dict:
    report = inventory_factory(ROOT).record()
    state = _read(STATE, {})
    # Офлайн/онлайн телефона: алерт только по факту смены состояния.
    health = _read(ROOT / "data" / "android_gateway" / "health.json", {})
    phone_connected = bool(health.get("connected"))
    prev_connected = state.get("phone_connected")  # None при первом прогоне
    phone_alert_text = ""
    if prev_connected is True and not phone_connected:
        phone_alert_text = (
            "📵 <b>Телефон офлайн</b>\n"
            f"Устройство: {health.get('serial') or 'н/д'}\n"
            "ADB и Companion не отвечают. Проверьте Companion и сеть телефона.\n"
            "<i>Содержимое телефона не передавалось.</i>")
    elif prev_connected is False and phone_connected:
        phone_alert_text = "📱 <b>Телефон снова онлайн</b>\nADB и Companion доступны."
    app_changes = list(report.get("availability_drift") or [])
    version_changes = list(report.get("version_drift") or [])
    stale = int(report.get("calibrations_stale") or 0)
    changed = bool(app_changes or version_changes or stale)
    sent = False
    if alert and phone_alert_text and not bootstrap:
        try:
            _send(phone_alert_text)
            sent = True
        except Exception:
            pass
    if alert and changed and not bootstrap:
        sent = _send(
            "📦 <b>Изменение инвентаря телефона</b>\n"
            f"Изменений доступности приложений: {len(app_changes)}\n"
            f"Изменений версий/связи: {len(version_changes)}\n"
            f"Устаревших калибровок: {stale}\n\n"
            "<i>Названия чатов, содержимое приложений и личные данные не передавались.</i>"
        )
    _write(STATE, {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "availability_drift": app_changes, "version_drift": version_changes,
        "calibrations_stale": stale, "sent": sent, "bootstrap": bool(bootstrap),
        "phone_connected": phone_connected,
    })
    return {"status": "ok", "app_changes": len(app_changes), "version_changes": len(version_changes), "stale": stale, "sent": sent}


if __name__ == "__main__":
    args = set(sys.argv[1:])
    print(json.dumps(check(alert="--alert" in args, bootstrap="--bootstrap" in args), ensure_ascii=False))
