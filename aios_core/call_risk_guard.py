#!/usr/bin/env python3
"""
AIOS Call Risk & Fraud Guard Engine
Анализирует транскрипты звонков на предмет рисков (требования предоплаты на личные карты,
агрессия, попытки фрода, отступление от минимальной цены) и отправляет алерты.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("aios.call_risk")


def evaluate_call_risks(transcription_text: str, summary_text: str, contact_name: str, dialogue_id: str) -> Dict[str, Any]:
    """Оценивает уровень риска в звонке."""
    full_text = (transcription_text + " " + summary_text).lower()

    risk_flags = []
    risk_level = "LOW"
    risk_score = 0

    if "предоплат" in full_text or "на карту" in full_text:
        risk_flags.append("Требование предоплаты на личную карту")
        risk_score += 35

    if "срочно" in full_text or "сейчас" in full_text or "быстро" in full_text:
        risk_flags.append("Давление по срочности")
        risk_score += 20

    if "ниже" in full_text or "скидк" in full_text or "дешевле" in full_text:
        risk_flags.append("Запрос глубокой скидки")
        risk_score += 15

    if "проблем" in full_text or "претензи" in full_text or "жалоб" in full_text:
        risk_flags.append("Претензионный диалог")
        risk_score += 30

    if risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"

    result = {
        "dialogue_id": dialogue_id,
        "contact_name": contact_name,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_flags": risk_flags,
        "requires_alert": risk_level in ("MEDIUM", "HIGH")
    }

    if result["requires_alert"]:
        logger.warning(f"🚨 [Risk Guard Alert] Звонок {contact_name} имеет уровень риска {risk_level} ({risk_flags})")
        try:
            from tg_bot.treasury import _send_tg_message
            _send_tg_message(
                f"🚨 **[AIOS Risk Guard Alert] Рискованный разговор!**\n\n"
                f"👤 **Контакт**: `{contact_name}`\n"
                f"📊 **Уровень риска**: `{risk_level}` (Оценка: {risk_score})\n"
                f"⚠️ **Факторы риска**: {', '.join(risk_flags)}"
            )
        except Exception:
            pass

    return result


if __name__ == "__main__":
    res = evaluate_call_risks("Срочно переведи предоплату на карту прямо сейчас", "Предоплата", "[PRIVATE_CONTACT]", "diag_99")
    print("Risk evaluation:", res)
