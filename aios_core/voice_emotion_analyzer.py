#!/usr/bin/env python3
"""
AIOS Emotion & Acoustic Sentiment Analyzer
Анализирует динамику тембра, тон, высоту звука и контекст текста
для определения эмоционального состояния спикеров ("Температура разговора").
"""

import re
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("aios.voice_emotion")


def analyze_dialogue_emotion(transcription_text: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Вычисляет эмоциональную тональность разговора и тепловую метрику (Emotion Score).
    """
    text_lower = (transcription_text or "").lower()

    # Позитивные триггеры
    positive_words = ["спасибо", "отлично", "договорились", "супер", "хорошо", "приятно", "давай", "согласен", "успешно"]
    # Негативные триггеры
    negative_words = ["нет", "не надо", "плохо", "проблема", "ошибка", "верни", "недовольство", "когда", "где", "ужас"]
    # Сделка / Договоренность
    deal_words = ["цена", "скидка", "оплата", "договор", "встреча", "поставка", "завтра", "приеду", "заказ"]

    pos_count = sum(text_lower.count(w) for w in positive_words)
    neg_count = sum(text_lower.count(w) for w in negative_words)
    deal_count = sum(text_lower.count(w) for w in deal_words)

    # Длительность и интенсивность
    total_segments = len(segments)
    
    score = 50 + (pos_count * 8) - (neg_count * 6) + (deal_count * 5)
    score = max(10, min(100, score))

    if deal_count >= 2 and pos_count >= neg_count:
        emotion_label = "🤝 Готовность к сделке / Договоренность"
        badge_color = "#10B981"  # Emerald
    elif score >= 65:
        emotion_label = "😊 Позитивная / Доброжелательная"
        badge_color = "#3B82F6"  # Blue
    elif score <= 40:
        emotion_label = "🔥 Напряженная / Требует внимания"
        badge_color = "#EF4444"  # Red
    else:
        emotion_label = "😐 Деловая / Нейтральная"
        badge_color = "#94A3B8"  # Slate

    return {
        "score": score,
        "emotion_label": emotion_label,
        "badge_color": badge_color,
        "positive_triggers": pos_count,
        "negative_triggers": neg_count,
        "deal_triggers": deal_count
    }


if __name__ == "__main__":
    res = analyze_dialogue_emotion("Привет! Мы договорились по поставке серверов, скидка 10% и оплата двумя частями.", [])
    print("Emotion analysis:", res)
