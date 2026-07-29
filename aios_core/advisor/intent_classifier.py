"""Smart Intent Classifier with Real LLM Integration."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reasoning: str
    language: str  # 'uk', 'ru', 'en'

class SmartIntentClassifier:
    def __init__(self, use_llm: bool = False, llm_api_key: str | None = None):
        self.use_llm = use_llm
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.keyword_map = {
            "price_inquiry": ["цена", "сколько", "торг", "дешевле", "уступ", "скидк", "знижк", "ціна", "скільки", "торг"],
            "delivery_question": ["доставка", "новая почта", "укрпочта", "отправите", "самовывоз", "відправите", "новою поштою", "нова пошта"],
            "stock_check": ["в наличии", "осталось", "есть ли", "резерв", "наявності", "залишилось"],
            "greeting": ["здравствуйте", "добрый день", "привет", "доброго дня", "вітаю"],
            "complaint": ["брак", "не работает", "возврат", "обман", "жалоба", "повернення"],
        }
        self.ua_markers = ["як", "ціна", "наявності", "дякую", "будь ласка", "відправите", "грн"]
        self.ru_markers = ["как", "цена", "наличии", "спасибо", "пожалуйста", "отправите", "руб"]

    def detect_language(self, text: str) -> str:
        text = text.lower()
        ua_score = sum(1 for m in self.ua_markers if m in text)
        ru_score = sum(1 for m in self.ru_markers if m in text)
        # Характерные буквы алфавитов — сильный сигнал
        ua_score += sum(1 for ch in ("і", "ї", "є", "ґ") if ch in text)
        ru_score += sum(1 for ch in ("ы", "э", "ъ", "ё") if ch in text)
        if ua_score > ru_score: return "uk"
        if ru_score > ua_score: return "ru"
        # Ничья: кириллический текст без явных маркеров → ru (основной рынок)
        if any("Ѐ" <= c <= "ӿ" for c in text): return "ru"
        return "en"

    async def classify(self, message: str, context: dict | None = None) -> IntentResult:
        lang = self.detect_language(message)
        msg = message.lower()
        best, max_m = "general_inquiry", 0
        
        for intent, kws in self.keyword_map.items():
            m = sum(1 for k in kws if k in msg)
            if m > max_m: max_m, best = m, intent
            
        if max_m >= 1:
            return IntentResult(best, min(0.7 + max_m * 0.1, 0.95), f"{max_m} совпадений", lang)
            
        if self.use_llm and self.llm_api_key:
            return await self._classify_with_llm(message, lang)
            
        return IntentResult("general_inquiry", 0.5, "Эвристика не сработала, LLM отключен", lang)

    async def _classify_with_llm(self, message: str, lang: str) -> IntentResult:
        api_key = self.llm_api_key or os.getenv("LLM_API_KEY")
        # Поддерживает OpenAI, LocalAI, Ollama (через LLM_BASE_URL)
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        intents_list = ", ".join(self.keyword_map.keys())
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": f"Ты ассистент. Определи намерение (intent) сообщения. Доступные intents: {intents_list}. Ответь строго в формате JSON: {{\"intent\": \"...\", \"confidence\": 0.9, \"reasoning\": \"...\"}}"},
                            {"role": "user", "content": message}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Очистка от markdown-оберток, если LLM их добавила
                content = content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(content)
                
                return IntentResult(
                    intent=parsed.get("intent", "general_inquiry"),
                    confidence=float(parsed.get("confidence", 0.8)),
                    reasoning=parsed.get("reasoning", "LLM analysis"),
                    language=lang
                )
        except Exception as e:
            return IntentResult("general_inquiry", 0.5, f"LLM error: {e!s}", lang)
