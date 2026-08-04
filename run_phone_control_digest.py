#!/usr/bin/env python3
"""Daily metadata-only phone control center digest for the owner."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aios_core.phone_control_center import PhoneControlCenter

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "android_gateway" / "phone_control_digest_state.json"
TZ = ZoneInfo("Europe/Kyiv")


def _today() -> str:
    return datetime.now(TZ).date().isoformat()


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
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
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30):
        pass
    return True


def build_text(snapshot: dict) -> str:
    device = snapshot.get("device") or {}
    leads = snapshot.get("leads") or {}
    apps = snapshot.get("apps") or []
    timers = snapshot.get("timers") or {}
    banks = snapshot.get("banks") or []
    bank_tasks = snapshot.get("bank_tasks") or {}
    available = sum(1 for app in apps if app.get("available"))
    calibrated = sum(1 for app in apps if app.get("calibrated"))
    timers_ok = sum(1 for value in timers.values() if value)
    return "\n".join([
        "📱 <b>Ежедневная сводка AIOS · телефон</b>",
        f"ADB: {'✅' if device.get('connected') else '⚠️'} · Companion: {'✅' if device.get('companion') else '⚠️'}",
        f"Приложения: {available}/{len(apps)} · калиброваны: {calibrated}",
        f"Лиды: {leads.get('pending', 0)} · CRM follow-up: {leads.get('crm_open', 0)} · внимание: {leads.get('crm_attention', 0)} · просрочены: {leads.get('crm_overdue', 0)}",
        "Банки: " + (" · ".join(f"{bank.get('title')}: {bank.get('unread_notifications', 0)} уведомл." for bank in banks) if banks else "нет данных"),
        f"Банковские задачи: {bank_tasks.get('pending', 0)} · внимание: {bank_tasks.get('attention', 0)} · просрочены: {bank_tasks.get('overdue', 0)}",
        f"Таймеры: {timers_ok}/{len(timers)} · аудит: {snapshot.get('audit', {}).get('count', 0)}",
        "<i>Переписки, имена, номера, маршруты, координаты, фото и аудио не включаются.</i>",
    ])


def check(force: bool = False, dry_run: bool = False, bootstrap: bool = False, center_factory=PhoneControlCenter) -> dict:
    snapshot = center_factory(ROOT).snapshot()
    state = _read(STATE, {})
    today = _today()
    due = bool(force or state.get("last_date") != today)
    text = build_text(snapshot)
    sent = False
    if bootstrap:
        _write(STATE, {"last_date": today, "bootstrapped_at": datetime.now(TZ).isoformat(timespec="seconds")})
        due = False
    elif due and not dry_run:
        sent = _send(text)
        if sent:
            _write(STATE, {"last_date": today, "sent_at": datetime.now(TZ).isoformat(timespec="seconds")})
    return {
        "status": "ok", "due": due, "sent": sent, "dry_run": bool(dry_run), "bootstrap": bool(bootstrap),
        "snapshot_status": snapshot.get("status"), "text": text if dry_run else "",
    }


def main() -> int:
    args = set(sys.argv[1:])
    result = check(force="--force" in args, dry_run="--dry-run" in args, bootstrap="--bootstrap" in args)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
