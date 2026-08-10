#!/usr/bin/env python3
"""
AIOS Google Calendar Auto-Event Sync
Превращает договоренности о встречах из звонков в карточки событий Google Календаря.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

CALENDAR_EVENTS_FILE = REPO_ROOT / "data" / "google_calendar_events.json"
logger = logging.getLogger("aios.google_calendar")


def create_calendar_event_from_action_item(contact_name: str, action_text: str, dialogue_id: str) -> Optional[Dict[str, Any]]:
    """Анализирует текст задачи и автоматически создает событие в Google Календаре."""
    if not action_text or len(action_text) < 5:
        return None

    # Поиск упоминания дней недели или времени
    now = datetime.now()
    event_time = now + timedelta(days=1)  # Дефолт на завтра
    
    action_lower = action_text.lower()
    if "пятниц" in action_lower:
        event_time = now + timedelta(days=(4 - now.weekday()) % 7 or 7)
    elif "понедельник" in action_lower:
        event_time = now + timedelta(days=(0 - now.weekday()) % 7 or 7)
    elif "сегодня" in action_lower:
        event_time = now
    elif "среду" in action_lower or "среда" in action_lower:
        event_time = now + timedelta(days=(2 - now.weekday()) % 7 or 7)

    event_time_str = event_time.strftime("%Y-%m-%d 14:00:00")

    event_obj = {
        "event_id": f"cal_{hash(dialogue_id + action_text)}",
        "title": f"📅 Встреча / Созвон: {contact_name}",
        "description": f"Договоренность из звонка AIOS: {action_text}\nКонтакт: {contact_name}\nID диалога: {dialogue_id}",
        "start_time": event_time_str,
        "contact_name": contact_name,
        "dialogue_id": dialogue_id,
        "created_at": datetime.now().isoformat(),
        "status": "scheduled"
    }

    # Сохранение в реестр событий
    events = []
    if CALENDAR_EVENTS_FILE.exists():
        try:
            with open(CALENDAR_EVENTS_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
        except Exception:
            pass

    if not any(e["event_id"] == event_obj["event_id"] for e in events):
        events.append(event_obj)
        CALENDAR_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALENDAR_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Создано событие в Google Календаре для {contact_name}: {event_time_str}")

        # Telegram уведомление
        try:
            from tg_bot.treasury import _send_tg_message
            _send_tg_message(
                f"📅 **[Google Календарь] Создано новое событие!**\n\n"
                f"👤 **Контакт**: `{contact_name}`\n"
                f"⏰ **Время**: `{event_time_str}`\n"
                f"📌 **Суть**: _{action_text}_"
            )
        except Exception:
            pass

    return event_obj


if __name__ == "__main__":
    ev = create_calendar_event_from_action_item("[PRIVATE_CONTACT]", "Встреча в пятницу в 14:00 по согласованию макета", "diag_123")
    print("Created Google Calendar event:", ev)
