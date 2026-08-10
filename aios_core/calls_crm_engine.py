#!/usr/bin/env python3
"""
AIOS Calls & Voice CRM Engine
Связывает расшифровки звонков, диктофонные записи (!voice), спикеров и контакты Google.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.whisper_colab_transcriber import CALLS_DIR
from aios_core.google_contacts_sync import load_google_contacts, match_folder_to_google_contact

logger = logging.getLogger("aios.calls_crm")


def get_all_dialogues() -> List[Dict[str, Any]]:
    """Собирает список всех звонков и диктофонных записей из папки /root/AIOS/Calls/."""
    dialogues = []
    if not CALLS_DIR.exists():
        return dialogues

    json_files = [f for f in CALLS_DIR.rglob("*.json") if not f.name.endswith("_cache.json")]

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            stem = jf.stem
            
            # Связанное резюме
            summary_f = jf.parent / f"{stem}_summary.md"
            summary_text = summary_f.read_text(encoding="utf-8") if summary_f.exists() else ""

            # Имя папки и контакт
            folder_name = jf.parent.name if jf.parent != CALLS_DIR else stem
            contact_info = match_folder_to_google_contact(folder_name, str(jf))
            if contact_info and contact_info.get("name"):
                folder_name = contact_info.get("name")
            is_dictaphone = "!voice" in str(jf) or "voice" in jf.name.lower()
            
            contact_info = data.get("google_contact") or match_folder_to_google_contact(folder_name)

            data["dialogue_id"] = stem
            data["json_path"] = str(jf)
            data["summary"] = summary_text or data.get("summary", "")
            data["google_contact"] = contact_info
            data["is_dictaphone"] = is_dictaphone
            data["folder_name"] = folder_name

            dialogues.append(data)
        except Exception as e:
            logger.debug(f"Error reading {jf.name}: {e}")

    return dialogues


def get_contacts_with_dialogues() -> List[Dict[str, Any]]:
    """
    Возвращает только те контакты Google, для которых имеются сохраненные разговоры/звонки.
    Контакты с 0 диалогов автоматически скрываются.
    """
    dialogues = get_all_dialogues()
    contacts_map = {}

    for d in dialogues:
        c_info = d.get("google_contact", {})
        c_id = c_info.get("id") or c_info.get("name")
        c_name = c_info.get("name") or "Неизвестный контакт"

        if c_id not in contacts_map:
            contacts_map[c_id] = {
                "contact_id": c_id,
                "name": c_name,
                "phone": c_info.get("phone", ""),
                "email": c_info.get("email", ""),
                "role": c_info.get("role", "Google Контакт"),
                "initials": c_info.get("initials") or "".join([w[0].upper() for w in c_name.split()[:2]]) if c_name else "К",
                "dialogues_count": 0,
                "dictaphone_count": 0,
                "last_activity": "",
                "dialogues": []
            }

        contacts_map[c_id]["dialogues_count"] += 1
        if d.get("is_dictaphone"):
            contacts_map[c_id]["dictaphone_count"] += 1

        contacts_map[c_id]["dialogues"].append({
            "dialogue_id": d.get("dialogue_id"),
            "filename": d.get("filename"),
            "is_dictaphone": d.get("is_dictaphone"),
            "duration_seconds": d.get("duration_seconds", 0),
            "language": d.get("language", "ru"),
            "summary_preview": (d.get("summary", "") or "")[:180],
            "transcription_preview": (d.get("transcription", "") or "")[:150],
            "segments_count": d.get("segments_count", 0)
        })

    # Фильтрация: отбрасываем контакты с 0 диалогов
    result_contacts = [c for c in contacts_map.values() if c["dialogues_count"] > 0]
    result_contacts.sort(key=lambda x: x["dialogues_count"], reverse=True)

    return result_contacts


def get_contact_dialogues_detail(contact_id: str) -> Optional[Dict[str, Any]]:
    """Возвращает информацию по конкретному контакту и все его диалоги."""
    contacts = get_contacts_with_dialogues()
    for c in contacts:
        if str(c["contact_id"]).casefold() == str(contact_id).casefold() or c["name"].casefold() == str(contact_id).casefold():
            return c
    return None


def get_single_dialogue_detail(dialogue_id: str) -> Optional[Dict[str, Any]]:
    """Возвращает подробную информацию о конкретном диалоге."""
    dialogues = get_all_dialogues()
    for d in dialogues:
        if d.get("dialogue_id") == dialogue_id or d.get("filename") == dialogue_id:
            c_info = d.get("google_contact", {})
            speakers = [
                {"id": "owner", "name": "Я (Владелец)", "role": "Владелец телефона", "is_owner": True},
                {"id": c_info.get("id"), "name": c_info.get("name", "Собеседник"), "role": c_info.get("role", "Google Контакт"), "is_owner": False}
            ]
            d["speakers"] = speakers
            return d
    return None


if __name__ == "__main__":
    contacts = get_contacts_with_dialogues()
    print(f"Контактов с диалогами: {len(contacts)}")
    for c in contacts[:5]:
        print(f" - {c['name']} ({c['phone']}): {c['dialogues_count']} диалогов")
