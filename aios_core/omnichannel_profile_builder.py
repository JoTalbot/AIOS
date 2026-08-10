#!/usr/bin/env python3
"""
AIOS Omnichannel 360° Contact Identity Profile Builder
Объединяет информацию о контакте из всех источников в единый профиль:
Google Contacts + Телефонные звонки + Записи окружения (!voice) + OLX + Viber + Telegram + Сделки.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues
from aios_core.google_contacts_sync import load_google_contacts

logger = logging.getLogger("aios.omnichannel")


def build_360_omnichannel_profile(contact_id_or_phone: str) -> Dict[str, Any]:
    """Строит сквозной профиль 360° по всем каналам коммуникаций."""
    contacts = get_contacts_with_dialogues()
    
    matched = None
    for c in contacts:
        if str(c["contact_id"]).casefold() == str(contact_id_or_phone).casefold() or c["name"].casefold() == str(contact_id_or_phone).casefold() or (c.get("phone") and c["phone"] in contact_id_or_phone):
            matched = c
            break

    if not matched:
        matched = {
            "contact_id": contact_id_or_phone,
            "name": str(contact_id_or_phone),
            "phone": contact_id_or_phone if "+" in contact_id_or_phone else "",
            "role": "Google Контакт",
            "dialogues_count": 0,
            "dialogues": []
        }

    # Поиск связанных сообщений в OLX / Viber / Telegram из converge_thread_cache.json
    converge_cache_f = REPO_ROOT / "data" / "converge_thread_cache.json"
    omnichannel_threads = []
    if converge_cache_f.exists():
        try:
            threads = json.loads(converge_cache_f.read_text(encoding="utf-8"))
            for t in threads:
                if matched["name"].lower() in str(t.get("title", "")).lower() or (matched.get("phone") and matched["phone"] in str(t.get("preview", ""))):
                    omnichannel_threads.append({
                        "channel": t.get("channel", "chat"),
                        "channel_label": t.get("channel_label", "Чат"),
                        "title": t.get("title"),
                        "preview": t.get("preview"),
                        "date": t.get("date")
                    })
        except Exception:
            pass

    profile = {
        "contact_id": matched["contact_id"],
        "name": matched["name"],
        "phone": matched.get("phone", ""),
        "email": matched.get("email", ""),
        "role": matched.get("role", "Google Контакт"),
        "initials": matched.get("initials", "К"),
        "omnichannel_channels": ["Google Contacts", "Phone Calls", "Ambient Dictaphone", "Converge CRM"],
        "calls_count": matched.get("dialogues_count", 0),
        "messages_count": len(omnichannel_threads),
        "dialogues": matched.get("dialogues", []),
        "messenger_history": omnichannel_threads
    }

    return profile


if __name__ == "__main__":
    prof = build_360_omnichannel_profile("[PRIVATE_CONTACT]")
    print("360 Profile:", prof["name"], "Channels:", prof["omnichannel_channels"])
