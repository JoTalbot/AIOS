#!/usr/bin/env python3
"""
AIOS Dialogue Entity & Intent Extractor
Извлекает ключевые сущности из разговоров: Авто/Запчасти, Город/Новая Почта, Цены, Даты, Имена.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTITIES_DB_FILE = REPO_ROOT / "data" / "dialogue_entities_db.json"

logger = logging.getLogger("aios.dialogue_entities")


def extract_entities_from_dialogue(transcription_text: str, summary_text: str) -> Dict[str, Any]:
    """Извлекает структурированные сущности из текста разговора."""
    text = (transcription_text + " " + summary_text)

    # 1. Поиск цен и сумм
    prices = re.findall(r'(\d+\s*(?:грн|грн\.|грн|usd|\$|долл|тыс))', text, re.IGNORECASE)

    # 2. Поиск Новой Почты и городов
    locations = re.findall(r'(киев|харьков|днепр|одесса|львов|запорожье|кривой рог|николаев|винница|полтава|черкассы|новая почта|отделение\s*№?\s*\d+)', text, re.IGNORECASE)

    # 3. Поиск марка/модель авто и запчастей
    auto_parts = re.findall(r'(bmw|mercedes|audi|vw|volkswagen|тойота|тойоту|фара|бампер|капот|дверь|сервер|модуль|двигатель|стекло|крыло)', text, re.IGNORECASE)

    entities = {
        "prices": list(set(prices))[:5],
        "locations": list(set(locations))[:5],
        "auto_parts": list(set(auto_parts))[:5]
    }

    return entities


if __name__ == "__main__":
    res = extract_entities_from_dialogue("Фара BMW X5 цена 1500 грн, доставка Новая Почта отделение №12 Киев", "")
    print("Extracted entities:", res)
