#!/usr/bin/env python3
"""
Напоминание «клиенты ждут ответа» (каждые 2 часа):
уведомления iMe/WhatsApp/OLX старше 2ч (но не старше 24ч), по которым
нет ни выполненной задачи, ни черновика в need_confirm → напоминание владельцу.
Если черновик есть, но не подтверждён — напоминание «черновик ждёт confirm N».
Один сводный TG-месcедж за прогон, дедуп по уведомлению.
"""
from __future__ import annotations

import html
import json
import os
import sqlite3
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTES = ROOT / "data" / "android_gateway" / "notifications.json"
QUEUE = ROOT / "data" / "android_gateway" / "phone_brain.db"
STATE = ROOT / "data" / "waiting_clients_state.json"
APPS = {"com.iMe.android": "iMe", "com.whatsapp": "WhatsApp", "ua.slando": "OLX"}


def _env(key: str) -> str:
    v = os.environ.get(key, "")
    if v:
        return v
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": html.escape(text)[:3900], "parse_mode": "HTML"}
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except Exception:
        return False


def run(dry: bool = False) -> dict:
    now = datetime.now()
    lo = (now - timedelta(hours=24)).isoformat()
    hi = (now - timedelta(hours=2)).isoformat()
    try:
        notes = json.loads(NOTES.read_text(encoding="utf-8"))
    except Exception:
        notes = []
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {"reminded": {}}
    reminded = state.get("reminded") or {}

    # контакты с черновиками в need_confirm
    pending = {}
    try:
        con = sqlite3.connect(QUEUE)
        for r in con.execute("select id, payload from jobs where status='need_confirm'"):
            p = json.loads(r[1] or "{}")
            c = str((p.get("params") or {}).get("contact") or "")
            if c:
                pending[c] = r[0]
    except Exception:
        pass

    waiting, drafted = {}, {}
    for n in notes if isinstance(notes, list) else []:
        pkg = str(n.get("package") or "")
        at = str(n.get("collected_at") or "")
        nid = str(n.get("id") or "")
        if pkg not in APPS or not (lo <= at <= hi) or nid in reminded:
            continue
        title = str(n.get("title") or "").strip()
        if not title or title in APPS.values() or len(title) < 3:
            continue  # сервисные уведомления
        reminded[nid] = now.isoformat(timespec="seconds")
        key = (APPS[pkg], title)
        if title in pending:
            drafted[key] = (f"• {APPS[pkg]} · {title}: черновик #{pending[title]} "
                            f"ждёт «confirm {pending[title]}»")
        else:
            waiting[key] = f"• {APPS[pkg]} · {title} — пишет с {at[11:16]}, ответа/черновика нет"
    state["reminded"] = {k: v for k, v in list(reminded.items())[-1000:]}
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    if not waiting and not drafted:
        return {"status": "ok", "sent": 0, "note": "никто не ждёт"}
    lines = ["⏳ <b>Клиенты ждут реакции:</b>"]
    lines += list(waiting.values())[:6] + list(drafted.values())[:4]
    text = "\n".join(lines)
    if dry:
        print(text)
        return {"status": "ok", "sent": 0, "waiting": len(waiting), "drafted": len(drafted)}
    sent = 1 if _tg(text) else 0
    return {"status": "ok", "sent": sent, "waiting": len(waiting), "drafted": len(drafted)}


def main() -> int:
    import sys
    print(json.dumps(run(dry="--dry" in sys.argv), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
