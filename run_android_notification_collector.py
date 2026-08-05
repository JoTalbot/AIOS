#!/usr/bin/env python3
"""Сбор уведомлений выбранных Android-приложений в общий инбокс AIOS."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from aios_core.android_gateway import AndroidGateway

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "android_gateway" / "notifications.json"
STATE = ROOT / "data" / "android_gateway" / "notification_alerts_state.json"
MAX_ITEMS = 150

APP_LABELS = {
    "com.whatsapp": "WhatsApp",
    "ua.com.abank": "A-Bank",
    "ua.privatbank.ap24": "Privat24",
    "ua.com.uklontaxi": "Uklon",
    "ua.com.uklon.uklondriver": "Uklon Driver",
    "com.iMe.android": "iMe Messenger",
    "com.eway": "EasyWay",
}


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
    path.chmod(0o600)


def _mask(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\b\d{4,8}\b", "••••", text)  # OTP/PIN and short sensitive codes
    text = re.sub(r"\b(?:\d[ -]?){12,19}\b", "••••", text)  # card-like values
    return text[:300]


def _event_id(event: dict) -> str:
    raw = "|".join(str(event.get(k) or "") for k in ("package", "title", "text", "posted_at"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def collect() -> dict:
    gateway = AndroidGateway(ROOT)
    result = gateway.notifications(limit=50)
    if result.get("status") != "ok":
        return {"status": result.get("status", "error"), "error": result.get("error", "")}
    existing = _read(DATA, [])
    state = _read(STATE, {"known": []})
    known = set(state.get("known") or [])
    existing_ids = {str(x.get("id")) for x in existing if isinstance(x, dict)}
    added = 0
    duplicates = 0
    for item in result.get("notifications") or []:
        package = str(item.get("package") or "")
        if package not in APP_LABELS:
            continue
        event_id = _event_id(item)
        if event_id in known or event_id in existing_ids:
            duplicates += 1
            continue
        existing.append({
            "id": event_id,
            "channel": "android",
            "app": APP_LABELS[package],
            "package": package,
            "title": _mask(item.get("title")),
            "text": _mask(item.get("text")),
            "posted_at": item.get("posted_at"),
            "read": False,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        known.add(event_id)
        added += 1
    existing = existing[-MAX_ITEMS:]
    _write(DATA, existing)
    _write(STATE, {"known": list(known)[-500:], "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    # The lead queue stores only notification identity/source/timestamp — never
    # title, preview or sender — and does not create CRM customers automatically.
    lead_result = {"status": "skipped", "added": 0}
    bank_result = {"status": "skipped", "added": 0}
    try:
        from aios_core.android_leads import AndroidLeadQueue
        lead_result = AndroidLeadQueue(ROOT).sync()
    except Exception:
        # Notification collection must remain available if an optional queue
        # maintenance task cannot run.
        pass
    try:
        from aios_core.android_bank_monitor import AndroidBankMonitor
        bank_result = AndroidBankMonitor(ROOT).sync_tasks()
    except Exception:
        pass
    return {"status": "ok", "added": added, "duplicates": duplicates, "total": len(existing),
            "lead_candidates_added": int(lead_result.get("added") or 0),
            "bank_tasks_added": int(bank_result.get("added") or 0)}


def mark_read() -> dict:
    entries = _read(DATA, [])
    changed = 0
    for entry in entries:
        if not entry.get("read"):
            entry["read"] = True
            changed += 1
    _write(DATA, entries)
    return {"status": "ok", "marked": changed}


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "collect"
    result = collect() if command == "collect" else mark_read() if command == "mark-read" else {"status": "error", "error": "collect|mark-read"}
    print(json.dumps(result, ensure_ascii=False))
    # Офлайн/ненастроенный телефон — штатный пропуск цикла, а не ошибка:
    # watchdog шлюза и инвентарь-алерты уже сообщают о недоступности устройства.
    if result.get("status") in ("offline", "unconfigured"):
        return 0
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
