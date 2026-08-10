#!/usr/bin/env python3
"""
AIOS Omnichannel Unified Contact Profile 360° (Option 5)
Объединяет все каналы взаимодействия (Google Contact, Звонки, Диктофон, OLX, Viber, Telegram)
в единую хронологическую 360° ленту клиента.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues

logger = logging.getLogger("aios.omnichannel")


def build_omnichannel_profile_360(contact_id: str) -> Dict[str, Any]:
    """Строит единый профиль клиента 360° из всех доступных каналов."""
    contacts = get_contacts_with_dialogues()
    matched = None
    for c in contacts:
        if str(c["contact_id"]).casefold() == str(contact_id).casefold() or c["name"].casefold() == str(contact_id).casefold():
            matched = c
            break

    if not matched:
        return {"status": "error", "reason": "Контакт не найден"}

    timeline = []

    # 1. Добавляем звонки и диктофон
    for d in matched.get("dialogues", []):
        timeline.append({
            "channel": "dictaphone" if d.get("is_dictaphone") else "phone_call",
            "channel_label": "Запись окружения" if d.get("is_dictaphone") else "Телефонный звонок",
            "icon": "mic" if d.get("is_dictaphone") else "call",
            "title": f"Разговор {d.get('filename')}",
            "preview": d.get("summary_preview") or d.get("transcription_preview"),
            "duration": d.get("duration_seconds", 0)
        })

    # 2. Поиск связанных сообщений из OLX / Viber / Telegram
    converge_cache = REPO_ROOT / "data" / "converge_thread_cache.json"
    if converge_cache.exists():
        try:
            with open(converge_cache, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                for thread_id, thread in c_data.items():
                    if matched["name"].lower() in str(thread).lower() or (matched["phone"] and matched["phone"] in str(thread)):
                        timeline.append({
                            "channel": thread.get("channel", "chat"),
                            "channel_label": f"Чат {thread.get('channel', 'Messenger').upper()}",
                            "icon": "chat",
                            "title": thread.get("title", "Сообщение"),
                            "preview": thread.get("preview", ""),
                            "duration": 0
                        })
        except Exception:
            pass

    return {
        "contact_id": matched["contact_id"],
        "name": matched["name"],
        "phone": matched["phone"],
        "email": matched["email"],
        "role": matched["role"],
        "channels_connected": ["Google Contacts", "Phone Calls", "Dictaphone Ambient", "OLX/Viber/Telegram"],
        "total_interactions": len(timeline),
        "timeline": timeline
    }


if __name__ == "__main__":
    prof = build_omnichannel_profile_360("c_6")
    print("Omnichannel 360 profile:", prof)
