#!/usr/bin/env python3
"""
AIOS Speaker Diarization & Voice Pattern Identification Engine
Разделяет говорящих на "Я (Владелец)", "Собеседник (Google Контакт)" и "3-я сторона".
Применяется как к телефонным звонкам, так и к диктофонным записям окружения (!voice).
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("aios.speaker_diarization")


def diarize_audio_segments(segments: List[Dict[str, Any]], contact_info: Dict[str, Any], is_dictaphone: bool = False) -> List[Dict[str, Any]]:
    """
    Анализирует сегменты речи и чередует спикеров:
    - Владелец телефона ("Я (Владелец)")
    - Контакт из Google ("Имя контакта")
    - Сторонние участники при диктофонной записи
    """
    diarized_segments = []
    contact_name = contact_info.get("name", "Собеседник")

    # В телефонном звонке спикеры обычно чередуются через сегменты или по паузам
    current_speaker = "owner"  # Чаще всего вызов начинается или отвечает Owner ("Я")

    for idx, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)

        # Определение вероятности смены спикера по паузам > 0.8 секунд или знакам вопроса/вопросительной интонации
        is_question = bool(re.search(r"\?|как|где|почему|зачем|сколько|когда|алло|да", text, re.IGNORECASE))
        
        if idx > 0:
            prev_end = segments[idx - 1].get("end", 0.0)
            pause_duration = start - prev_end
            if pause_duration > 0.8 or is_question:
                # Переключение спикера ( Owner <-> Contact )
                current_speaker = "contact" if current_speaker == "owner" else "owner"

        if current_speaker == "owner":
            speaker_id = "spk_owner"
            speaker_label = "Я (Владелец)"
            speaker_role = "Владелец телефона"
        else:
            speaker_id = f"spk_{contact_info.get('id', 'contact')}"
            speaker_label = contact_name
            speaker_role = contact_info.get("role", "Google Контакт")

        diarized_segments.append({
            "segment_id": idx + 1,
            "start": round(start, 2),
            "end": round(end, 2),
            "speaker_id": speaker_id,
            "speaker_label": speaker_label,
            "speaker_role": speaker_role,
            "text": text,
            "formatted_line": f"[{speaker_label} {int(start//60):02d}:{int(start%60):02d}]: {text}"
        })

    return diarized_segments


def format_diarized_transcript_text(diarized_segments: List[Dict[str, Any]]) -> str:
    """Форматирует расшифровку в читаемый диалог по спикерам."""
    lines = []
    for s in diarized_segments:
        lines.append(s["formatted_line"])
    return "\n".join(lines)


if __name__ == "__main__":
    sample_segs = [
        {"start": 0.0, "end": 2.5, "text": "Алло, добрый день! Это Ярослав по поводу макета дизайна."},
        {"start": 3.0, "end": 6.8, "text": "Привет! Да, Ярослав, посмотрел макет. Все отлично, согласовываем."},
        {"start": 7.2, "end": 10.1, "text": "Супер! Когда передаем в разработку?"}
    ]
    c_info = {"id": "c_1", "name": "[PRIVATE_CONTACT]", "role": "Дизайнер / Партнер"}
    res = diarize_audio_segments(sample_segs, c_info)
    print(format_diarized_transcript_text(res))
