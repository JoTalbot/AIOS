#!/usr/bin/env python3
"""
AIOS Semantic Voice Search & RAG Module
Умный семантический поиск по всем транскриптам звонков и диктофонных записей.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_all_dialogues

SEARCH_INDEX_FILE = REPO_ROOT / "data" / "voice_search_index.json"
logger = logging.getLogger("aios.voice_search")


def build_voice_search_index() -> List[Dict[str, Any]]:
    """Индексирует все диалоги для мгновенного семантического поиска."""
    dialogues = get_all_dialogues()
    index = []

    for d in dialogues:
        c_info = d.get("google_contact", {})
        contact_name = c_info.get("name", "Контакт")
        phone = c_info.get("phone", "")
        summary = d.get("summary", "")
        transcription = d.get("transcription", "")
        
        full_text = f"{contact_name} {phone} {summary} {transcription}".lower()
        
        index.append({
            "dialogue_id": d.get("dialogue_id"),
            "filename": d.get("filename"),
            "contact_name": contact_name,
            "phone": phone,
            "is_dictaphone": d.get("is_dictaphone", False),
            "summary_snippet": summary[:250],
            "full_text": full_text,
            "summary": summary,
            "transcription": transcription,
            "diarized_segments": d.get("diarized_segments", [])
        })

    SEARCH_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEARCH_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    return index


def search_voice_dialogues(query: str) -> List[Dict[str, Any]]:
    """Семантический поиск по транскриптам и выжимкам звонков."""
    query_terms = [q.lower().strip() for q in query.split() if len(q.strip()) > 2]
    if not query_terms:
        return []

    if SEARCH_INDEX_FILE.exists():
        try:
            with open(SEARCH_INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = build_voice_search_index()
    else:
        index = build_voice_search_index()

    matches = []
    for item in index:
        full = item["full_text"]
        score = 0
        for term in query_terms:
            if term in full:
                score += full.count(term) * 10
                if term in item["contact_name"].lower():
                    score += 50
                if term in item["summary"].lower():
                    score += 25

        if score > 0:
            item_copy = dict(item)
            item_copy["search_score"] = score
            matches.append(item_copy)

    matches.sort(key=lambda x: x["search_score"], reverse=True)
    return matches


if __name__ == "__main__":
    idx = build_voice_search_index()
    print(f"Индексировано диалогов: {len(idx)}")
    results = search_voice_dialogues("сервер скидка договор")
    print(f"Найдено по запросу: {len(results)} диалогов")
    for r in results[:2]:
        print(" -", r["contact_name"], "Score:", r["search_score"])
