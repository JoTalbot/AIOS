#!/usr/bin/env python3
"""Weekly metadata-only AIOS phone/lead report."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from aios_core.android_audit import PhoneActionAudit
from aios_core.android_leads import AndroidLeadQueue
from aios_core.phone_control_center import PhoneControlCenter

ROOT = Path(__file__).resolve().parent


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


def build_text(root: Path = ROOT, days: int = 7) -> str:
    metrics = AndroidLeadQueue(root).weekly_metrics(days)
    control = PhoneControlCenter(root).snapshot()
    audit_events = PhoneActionAudit(root).recent(limit=500)
    return "\n".join([
        f"📊 <b>Недельный отчёт AIOS · телефон · {metrics['days']} дн.</b>",
        f"Лиды: новые {metrics['leads_created']} · обработаны {metrics['leads_reviewed']} · переведены в follow-up {metrics['leads_promoted']}",
        f"CRM follow-up: созданы {metrics['tasks_created']} · закрыты {metrics['tasks_completed']} · открыты {metrics['tasks_open']} · внимание {metrics['tasks_attention']} · просрочены {metrics['tasks_overdue']}",
        f"Телефон: {'✅ ADB' if control.get('device', {}).get('connected') else '⚠️ ADB'} · {'✅ Companion' if control.get('device', {}).get('companion') else '⚠️ Companion'}",
        "Банки: " + (" · ".join(f"{bank.get('title')}: {bank.get('unread_notifications', 0)} уведомл." for bank in (control.get('banks') or [])) if control.get('banks') else "нет данных"),
        f"Банковские задачи: {(control.get('bank_tasks') or {}).get('pending', 0)} · внимание: {(control.get('bank_tasks') or {}).get('attention', 0)} · просрочены: {(control.get('bank_tasks') or {}).get('overdue', 0)}",
        f"Безопасный аудит: {len(audit_events)} технических событий в журнале",
        "<i>Тексты чатов, имена, номера, маршруты, координаты, фото и аудио не включаются.</i>",
    ])


def main() -> int:
    args = set(sys.argv[1:])
    days = next((int(value) for value in sys.argv[1:] if value.isdigit()), 7)
    text = build_text(days=days)
    sent = _send(text) if "--send" in args else False
    print(json.dumps({"status": "ok", "days": days, "sent": sent, "text": "" if sent else text}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
