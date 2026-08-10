#!/usr/bin/env python3
"""
AIOS Smart Follow-up & Sales Script Generator
Генерирует готовые шаблоны сообщений клиенту (Viber / Telegram / SMS) по итогам разговора.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("aios.followup")


def generate_dialogue_followup_message(contact_name: str, summary_text: str, transcription_text: str) -> Dict[str, Any]:
    """Генерирует драфт follow-up сообщения клиенту по итогам разговора."""
    prompt = f"""
На основе транскрипта и выжимки телефонного разговора сформируй готовое короткое вежливое сообщение для клиента в Viber/Telegram:

Контакт: {contact_name}
Выжимка разговора:
\"\"\"
{summary_text[:500]}
\"\"\"

Сообщение должно содержать:
1. Вежливое приветствие.
2. Подтверждение ключевых договоренностей (цена, товар/услуга, дата).
3. Призыв к действию / Следующий шаг (например: "Отправляю реквизиты для оплаты" или "Ждем вас в пятницу в 14:00").
"""
    try:
        from aios_core.llm_balancer import LLMBalancer
        balancer = LLMBalancer()
        followup_msg = balancer.chat(
            messages=[{"role": "user", "content": prompt}],
            system="Ты — менеджер по клиентскому сервису и продажам AIOS."
        )
    except Exception as e:
        logger.warning(f"Followup generation error: {e}")
        followup_msg = f"Добрый день, {contact_name}! Благодарим за звонок. Подтверждаем наши договоренности. Хорошего дня!"

    return {
        "contact_name": contact_name,
        "followup_draft": followup_msg.strip(),
        "viber_ready": True,
        "telegram_ready": True
    }


if __name__ == "__main__":
    res = generate_dialogue_followup_message("[PRIVATE_CONTACT]", "Договорились о скидке 10% на фару BMW X5 и оплате двумя частями.", "")
    print("Followup Draft:", res["followup_draft"])
