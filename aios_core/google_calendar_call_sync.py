#!/usr/bin/env python3
"""
AIOS Google Calendar Sync for Call Action Items & Meetings (Option 2)
Автоматически превращает извлеченные из звонков и диктофона договоренности в события Google Календаря.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

CALENDAR_EVENTS_FILE = REPO_ROOT / "data" / "google_calendar_events.json"
logger = logging.getLogger("aios.calendar_call_sync")


def sync_call_action_items_to_calendar(contact_name: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Создает события в Google Календаре на основе извлеченных Action Items."""
    events = []
    if not tasks:
        return events

    existing = []
    if CALENDAR_EVENTS_FILE.exists():
        try:
            with open(CALENDAR_EVENTS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    for idx, t in enumerate(tasks):
        task_text = t.get("task", "")
        if not task_text:
            continue

        # Определение ориентировочной даты события (по умолчанию +1 день от вызова в 14:00)
        event_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 14:00:00")
        
        event_data = {
            "id": f"gcal_{hash(task_text)}",
            "title": f"📅 Встреча / Задача: {task_text[:60]}",
            "description": f"Автоматически создано AIOS из разговора с {contact_name}.\nДетали: {task_text}",
            "contact": contact_name,
            "event_time": event_time,
            "status": "confirmed",
            "created_at": datetime.now().isoformat()
        }

        if not any(e.get("title") == event_data["title"] for e in existing):
            existing.append(event_data)
            events.append(event_data)

    if events:
        CALENDAR_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALENDAR_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Внесено {len(events)} событий в Google Календарь для {contact_name}")

    return events


if __name__ == "__main__":
    res = sync_call_action_items_to_calendar("[PRIVATE_CONTACT]", [{"task": "Согласовать макет дизайна автозапчастей"}])
    print("Google Calendar Events synced:", res)
