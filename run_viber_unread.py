#!/usr/bin/env python3
"""Сбор непрочитанных сообщений Viber с телефона.

Читает активные уведомления Viber (com.viber.voip) через
`adb shell dumpsys notification --noredact` — это то, что телефон показывает
как непрочитанное: title = контакт, text = текст сообщения.

Служебные уведомления (реклама Rakuten, «лайфгаки», «новини», системные)
отфильтровываются — остаются только личные сообщения.

Сохраняет в data/viber_unread.json (свежий снимок) — оттуда результат
показывается в Telegram-боте по команде «вайбер» / «непрочитанные вайбер».

CLI:
  python run_viber_unread.py          # собрать и вывести список
  python run_viber_unread.py --json   # вывести JSON
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "viber_unread.json"
ADB = "/usr/local/bin/aios-adb"

# Служебные Viber-уведомления (реклама/система) — не личные сообщения
_SERVICE_MARKERS = (
    "rakuten", "лайфгак", "новини", "хайлайт", "highlight", "новости", "реклам",
    "промо", "promo", "сообщество", "community", "группа создана", "вы добавлены",
    "подключен", "устройство", "защита", "резервн", "обновлен", "рекомендуем",
    "скидк", "акци", "розыгрыш", "приз", "голосовани", "опрос", "sticker", "стикер",
)


def _adb(args, timeout: int = 60) -> str:
    r = subprocess.run([ADB, "shell", *args], capture_output=True,
                       text=True, timeout=timeout)
    return r.stdout or ""


def collect() -> dict:
    """Собрать активные Viber-уведомления (непрочитанные)."""
    out = _adb(["dumpsys", "notification", "--noredact"])
    records = re.split(r"NotificationRecord\(", out)
    items = []
    for rec in records:
        head = rec.split("Notification(", 1)[0] if "Notification(" in rec else rec[:200]
        if "com.viber.voip" not in head:
            continue
        title_m = re.search(r"android\.title=(?:String|SpannableString) \((.*?)\)\s*\n", rec, re.S)
        text_m = re.search(r"android\.text=(?:String|SpannableString) \((.*?)\)\s*\n", rec, re.S)
        title = title_m.group(1).strip() if title_m else ""
        text = text_m.group(1).strip() if text_m else ""
        # вытащить время (когда)
        when_m = re.search(r"when=(\d+)", rec)
        when = int(when_m.group(1)) / 1000 if when_m else 0
        ts = datetime.fromtimestamp(when).strftime("%d.%m %H:%M") if when else ""
        if not title and not text:
            continue
        items.append({"title": title, "text": text, "at": ts})

    # фильтр служебных
    personal = []
    for it in items:
        blob = f"{it['title']} {it['text']}".lower()
        if any(m in blob for m in _SERVICE_MARKERS):
            continue
        personal.append(it)

    snapshot = {
        "collected_at": datetime.now().strftime("%d.%m %H:%M"),
        "total_notifications": len(items),
        "messages": personal,
    }
    try:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return snapshot


def render(snapshot: dict) -> str:
    msgs = snapshot.get("messages") or []
    if not msgs:
        return ("💜 <b>Viber: непрочитанных личных сообщений нет</b>\n"
                "(проверено с телефона, " + str(snapshot.get("collected_at")) + ")")
    lines = [f"💜 <b>Viber: {len(msgs)} непрочитанных</b> (с телефона, "
             + str(snapshot.get("collected_at")) + ")"]
    for i, m in enumerate(msgs[:15], 1):
        who = m.get("title") or "?"
        txt = (m.get("text") or "").strip()
        lines.append(f"╭─ <code>{i:02d}</code> <b>{who}</b>{' · ' + m['at'] if m.get('at') else ''}")
        if txt:
            lines.append(f"├ {txt[:200]}")
        lines.append("├ Ответить: «ответь на вайбер {0}: текст»".format(i))
    return "\n".join(lines)


def main() -> int:
    snap = collect()
    if "--json" in sys.argv:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    else:
        print(render(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
