#!/usr/bin/env python3
"""Алерт о низкой батарее телефона G1: <20% и не заряжается → TG-алерт владельцу.

Читает свежий health из Companion напрямую; состояние зарядки — через adb.
Кулдаун 1 час, чтобы не спамить. Ничего не меняет на устройстве.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "android_gateway" / "battery_alert_state.json"
THRESHOLD = 20
COOLDOWN_SECONDS = 3600


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


def _read_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _send(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except (urllib.error.URLError, OSError):
        return False


def _companion_health() -> dict:
    cfg = {}
    try:
        cfg = json.loads((ROOT / "data" / "android_gateway" / "companion.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    endpoint = str(cfg.get("endpoint") or "").rstrip("/")
    token = str(cfg.get("token") or "")
    if not endpoint or len(token) < 16:
        return {}
    req = urllib.request.Request(endpoint + "/health", headers={"X-AIOS-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (urllib.error.URLError, OSError, ValueError):
        return {}


def _charging() -> bool | None:
    try:
        result = subprocess.run(
            ["/usr/local/bin/aios-adb", "shell", "dumpsys battery"],
            capture_output=True, text=True, timeout=15)
        out = result.stdout or ""
        ac = "AC powered: true" in out
        usb = "USB powered: true" in out
        wireless = "Wireless powered: true" in out
        return ac or usb or wireless
    except Exception:
        return None


def main() -> int:
    health = _companion_health()
    if health.get("status") != "ok":
        print(json.dumps({"status": "offline", "sent": False}, ensure_ascii=False))
        return 0
    battery = health.get("battery")
    if not isinstance(battery, int):
        print(json.dumps({"status": "error", "sent": False}, ensure_ascii=False))
        return 0
    charging = _charging()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state = _read_state()
    sent = False
    if battery < THRESHOLD and charging is False:
        last = str(state.get("last_sent") or "")
        if last:
            try:
                delta = (datetime.fromisoformat(now) - datetime.fromisoformat(last)).total_seconds()
            except ValueError:
                delta = COOLDOWN_SECONDS
            if delta < COOLDOWN_SECONDS:
                print(json.dumps({"status": "ok", "battery": battery, "sent": False,
                                  "reason": "cooldown"}, ensure_ascii=False))
                return 0
        sent = _send(f"🪫 <b>Телефон G1: батарея {battery}%</b> и НЕ заряжается. "
                     f"Поставьте на зарядку, иначе автоматика отвалится.")
        state["last_sent"] = now
        _write_state(state)
    print(json.dumps({"status": "ok", "battery": battery, "charging": charging,
                      "sent": sent}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
