#!/usr/bin/env python3
"""
AIOS Call Risk Guard & Fraud Monitor Engine (Option 4)
Сканирует транскрипты на предмет мошеннических рисков, аномальных требований и нарушений.
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


def detect_call_risks(contact_name: str, dialogue_id: str, transcript_text: str) -> Dict[str, Any]:
    """Сканирует диалог на предмет рисков и аномалий."""
    text_lower = (transcript_text or "").lower()

    risk_flags = []
    
    # 1. Финансовые аномалии
    if any(p in text_lower for p in ["без чека", "наличкой без документов", "предоплата 100%", "без договора"]):
        risk_flags.append("⚠️ Требование нерегулируемой оплаты или отсутствие документов")

    # 2. Недовольство или претензии
    if any(p in text_lower for p in ["плохо", "недоволен", "верните деньги", "не работает", "ужас", "жалоба"]):
        risk_flags.append("🚨 Недовольство клиента или претензия по качеству")

    # 3. Подозрительные фразы
    if any(p in text_lower for p in ["карта друга", "дистанционный доступ", "код из смс", "пароль"]):
        risk_flags.append("⛔ Критический риск: попытка запроса персональных данных / фрод")

    risk_level = "HIGH" if len(risk_flags) >= 2 else ("MEDIUM" if len(risk_flags) == 1 else "LOW")

    return {
        "dialogue_id": dialogue_id,
        "contact_name": contact_name,
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "has_risks": len(risk_flags) > 0
    }


if __name__ == "__main__":
    res = detect_call_risks("[PRIVATE_CONTACT]", "call_101", "Клиент недоволен качеством и требует вернуть деньги без договора.")
    print("Risk detection:", res)
