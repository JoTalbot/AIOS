"""
AIOS Customer Order & TTN Extractor (v19.0.0)
Интеллектуальный парсер данных доставки (ФИО, телефон, город, отделение НП) из переписки с клиентом.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from aios_core.llm_balancer import LLMBalancer

logger = logging.getLogger("AIOS.OrderExtractor")


class AIOSOrderExtractor:
    """ИИ-экстрактор реквизитов доставки и заказов из входящих сообщений."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        self.balancer = LLMBalancer()

    def extract_delivery_details(self, message_text: str) -> Dict[str, Any]:
        """Извлекает из сообщения ФИО, телефон, город, номер отделения Новой Почты и товар."""
        prompt = f"""
Проанализируй входящее сообщение от покупателя автозапчастей и извлеки структурированные данные доставки Новой Почты.

Сообщение покупателя:
\"\"\"{message_text}\"\"\"

Верни ТОЛЬКО валидный JSON со следующими полями:
{{
  "part_name": "название детали/товара (или пусто)",
  "price": число_в_грн_или_null,
  "recipient_name": "ФИО получателя",
  "phone": "+380XXXXXXXXX (в нормализованном виде)",
  "city": "Город (на украинском или русском)",
  "warehouse": "номер отделения Новой Почты (только цифра или строка)",
  "payment_type": "наложенный платеж / предоплата / не указано",
  "confidence": число_от_0_до_1
}}
"""
        try:
            raw_reply = self.balancer.chat(
                [{"role": "user", "content": prompt}],
                system="Ты ассистент логистики Новой Почты. Возвращай исключительно чистый JSON.",
                temperature=0.1,
                task_type="chat"
            )
            
            # Извлекаем JSON из ответа
            start = raw_reply.find("{")
            end = raw_reply.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw_reply[start:end])
                
                # Формируем готовый шаблон команды создания ТТН
                detail = data.get("part_name") or "Автозапчасть"
                cost = data.get("price") or 500
                fio = data.get("recipient_name") or "Получатель"
                phone = data.get("phone") or ""
                city = data.get("city") or ""
                wh = data.get("warehouse") or "1"
                
                ttn_cmd = f"создай ТТН: {detail}, {cost}, {fio}, {phone}, {city}, {wh}"
                
                return {
                    "status": "success",
                    "extracted_data": data,
                    "generated_ttn_command": ttn_cmd,
                    "ready_for_ttn": bool(fio and phone and city and wh)
                }
        except Exception as e:
            logger.error(f"Ошибка LLM экстракции заказа: {e}")

        # Fallback regex extraction
        phone_match = re.search(r'(\+?380\d{9}|0\d{9})', message_text)
        phone = phone_match.group(1) if phone_match else ""
        
        return {
            "status": "partial",
            "extracted_data": {
                "phone": phone,
                "raw_text": message_text
            },
            "ready_for_ttn": False
        }
