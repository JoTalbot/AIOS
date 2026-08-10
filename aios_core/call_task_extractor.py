#!/usr/bin/env python3
"""
AIOS Call Action Items & CRM Task Extractor
Извлекает задачи, даты встреч и обязательства из звонков и автоматически заносит их в CRM и напоминания.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
REMINDERS_FILE = REPO_ROOT / "data" / "reminders.json"

logger = logging.getLogger("aios.call_tasks")


def extract_and_save_call_tasks(dialogue_id: str, filename: str, summary_text: str, contact_name: str) -> List[Dict[str, Any]]:
    """Извлекает задачи из выжимки звонка и сохраняет в reminders.json."""
    if not summary_text or "Action Items" not in summary_text and "Следующие шаги" not in summary_text:
        return []

    tasks = []
    # Поиск блока Следующие шаги
    lines = summary_text.splitlines()
    in_action = False
    for line in lines:
        if "Action Items" in line or "Следующие шаги" in line:
            in_action = True
            continue
        if in_action:
            if line.startswith("📌") or line.startswith("👥") or line.startswith("💡") or line.startswith("🎭"):
                break
            clean_line = line.strip().lstrip("-").lstrip("*").lstrip("•").strip()
            if clean_line and len(clean_line) > 5:
                tasks.append({
                    "task": clean_line,
                    "contact": contact_name,
                    "filename": filename,
                    "dialogue_id": dialogue_id
                })

    if not tasks:
        return []

    # Сохранение в reminders.json
    existing = []
    if REMINDERS_FILE.exists():
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    updated = False
    for t in tasks:
        task_text = f"📞 [Звонок {contact_name}]: {t['task']}"
        if not any(e.get("text") == task_text for e in existing):
            existing.append({
                "id": f"rem_{hash(task_text)}",
                "text": task_text,
                "contact": contact_name,
                "dialogue_id": dialogue_id,
                "status": "pending",
                "source": "call_action_item"
            })
            updated = True

    if updated:
        REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Добавлено новых CRM-задач из звонка {contact_name}: {len(tasks)}")

    return tasks


if __name__ == "__main__":
    sample_summary = """
📌 **Тема**: Встреча
🎯 **Следующие шаги / Action Items**:
- Подтвердить встречу в пятницу в 14:00
- Отправить расчет стоимости договора
"""
    res = extract_and_save_call_tasks("diag_123", "call.mp3", sample_summary, "[PRIVATE_CONTACT]")
    print("Extracted tasks:", res)
