"""Напоминания Telegram-бота (выделено из run_telegram_bot.py).

Шаблоны ответов и напоминания: «напомни завтра в 15:00 …», повторяющиеся.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import _esc_tg, _safe

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_FILE = PROJECT_ROOT / "data" / "templates.json"
REMINDERS_FILE = PROJECT_ROOT / "data" / "reminders.json"


def _load_templates() -> dict:
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_templates(tpl: dict) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_reminders() -> list[dict]:
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_reminders(items: list[dict]) -> None:
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMINDERS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _handle_reminder(api, chat_id: int, text: str) -> None:
    """«напомни [завтра/сегодня/в] <HH:MM> <текст>» + повторяющиеся («каждый день/неделю/месяц»)."""
    text_clean = re.sub(r"^(напомни|напоминание|remind)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()

    # повторяющиеся: «напоминай каждый день в 09:00 ...»
    m_repeat = re.search(r"(каждый|каждую|раз в)\s+(день|неделю|месяц|утро|вечер)", text_clean.lower())
    if m_repeat:
        period = m_repeat.group(2)
        m_time = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text_clean)
        if m_time:
            hh, mm = int(m_time.group(1)), int(m_time.group(2))
            body = re.sub(r"^(напоминай|напомни)\s*(каждый|каждую|раз в)\s*(день|неделю|месяц|утро|вечер)\s*", "", text_clean, flags=re.IGNORECASE)
            body = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", body).strip()
            if "утро" in period:
                hh, mm = 9, 0
            elif "вечер" in period:
                hh, mm = 21, 0
            reminders = _load_reminders()
            reminders.append({
                "chat_id": chat_id,
                "at": datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0).isoformat(),
                "text": body or "(напоминание)",
                "repeat": period,
            })
            _save_reminders(reminders)
            api.send_message(chat_id, f"🔁 Напоминаю {period} в {hh:02d}:{mm:02d}: «{body[:100]}»")
            return
    # время HH:MM
    m_time = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text_clean)
    # день
    day_off = 0
    if any(w in text_clean.lower() for w in ("завтра", "tomorrow")):
        day_off = 1
    elif any(w in text_clean.lower() for w in ("послезавтра", "day after")):
        day_off = 2
    elif "через" in text_clean.lower():
        m_h = re.search(r"через\s+(\d+)\s*(час|ч|минут|мин)", text_clean.lower())
        if m_h:
            n = int(m_h.group(1))
            unit = m_h.group(2)
            now = datetime.now()
            if unit.startswith("ч"):
                target = now + timedelta(hours=n)
            else:
                target = now + timedelta(minutes=n)
            body = re.sub(r"через\s+\d+\s*(час|ч|минут|мин)\s*", "", text_clean, flags=re.IGNORECASE).strip()
            reminders = _load_reminders()
            reminders.append({"chat_id": chat_id, "at": target.isoformat(), "text": body})
            _save_reminders(reminders)
            api.send_message(chat_id, f"⏰ Напомню через {n} {unit} (в {target.strftime('%H:%M')}): «{body[:100]}»")
            return

    if not m_time:
        api.send_message(chat_id, "⏰ Формат: «напомни завтра в 15:00 позвонить Мише»\n"
                                  "или «напомни через 30 минут выпить воды»")
        return
    hh, mm = int(m_time.group(1)), int(m_time.group(2))
    body = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", text_clean).strip()
    body = re.sub(r"^(завтра|сегодня|послезавтра|tomorrow|today)\s*", "", body, flags=re.IGNORECASE).strip()
    body = re.sub(r"^в\s+", "", body, flags=re.IGNORECASE).strip()
    target = datetime.now() + timedelta(days=day_off)
    target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
    reminders = _load_reminders()
    reminders.append({"chat_id": chat_id, "at": target.isoformat(), "text": body or "(напоминание)"})
    _save_reminders(reminders)
    api.send_message(chat_id, f"⏰ Напомню {target.strftime('%d.%m %H:%M')}: «{body[:100]}»")


def _run_due_reminders() -> int:
    """Отправить созревшие напоминания (вызывается по таймеру и при старте бота)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("AIOS_TELEGRAM_TOKEN", "")
    reminders = _load_reminders()
    if not reminders:
        return 0
    now = datetime.now()
    due = [r for r in reminders if datetime.fromisoformat(r["at"]) <= now]
    if not due:
        return 0
    left = [r for r in reminders if datetime.fromisoformat(r["at"]) > now]
    for r in due:
        if not token:
            continue
        payload = json.dumps({"chat_id": r["chat_id"],
                              "text": f"⏰ <b>Напоминание</b>: {_esc_tg(r.get('text', ''))}",
                              "parse_mode": "HTML"}).encode()
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                         data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30):
                pass
            print(f"  [REMINDER] sent: {r.get('text', '')[:50]}")
        except Exception as e:
            print(f"  [REMINDER] err: {e}")
            left.append(r)  # попробуем ещё раз в следующий цикл
            continue
        # повторяющиеся: переносим на следующий период
        if r.get("repeat"):
            period = r["repeat"]
            nxt = now
            if period in ("день", "утро", "вечер"):
                nxt = now + timedelta(days=1)
            elif period == "неделю":
                nxt = now + timedelta(weeks=1)
            elif period == "месяц":
                month = now.month + 1
                year = now.year + (1 if month > 12 else 0)
                month = 1 if month > 12 else month
                try:
                    nxt = now.replace(year=year, month=month)
                except Exception:
                    nxt = now + timedelta(days=30)
            left.append({**r, "at": nxt.isoformat()})
    _save_reminders(left)
    return len(due)
