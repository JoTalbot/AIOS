"""Smart Intent Classifier with Lang Detect and LLM readiness."""
from __future__ import annotations
from typing import Dict, Optional
from dataclasses import dataclass
import os

@dataclass
class IntentResult:
    intent: str
    confidence: float
    reasoning: str
    language: str  # 'uk', 'ru', 'en'

class SmartIntentClassifier:
    def __init__(self, use_llm: bool = False, llm_api_key: Optional[str] = None):
        self.use_llm = use_llm
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.keyword_map = {
            "price_inquiry": ["цена", "сколько", "торг", "дешевле", "ціна", "скільки", "торг"],
            "delivery_question": ["доставка", "новая почта", "укрпочта", "отправите", "самовывоз", "відправите"],
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
        if ua_score > ru_score: return "uk"
        if ru_score > ua_score: return "ru"
        return "en"

    def classify(self, message: str, context: Optional[Dict] = None) -> IntentResult:
        lang = self.detect_language(message)
        msg = message.lower()
        best, max_m = "general_inquiry", 0
        
        for intent, kws in self.keyword_map.items():
            m = sum(1 for k in kws if k in msg)
            if m > max_m: max_m, best = m, intent
            
        if max_m >= 1:
            return IntentResult(best, min(0.7 + max_m * 0.1, 0.95), f"{max_m} совпадений", lang)
            
        if self.use_llm and self.llm_api_key:
            return self._classify_with_llm(message, lang)
            
        return IntentResult("general_inquiry", 0.5, "Эвристика не сработала, LLM отключен", lang)

    def _classify_with_llm(self, message: str, lang: str) -> IntentResult:
        # TODO: Реальный вызов OpenAI / Ollama API
        # response = requests.post("https://api.openai.com/v1/chat/completions", ...)
        return IntentResult("general_inquiry", 0.8, "LLM анализ (требуется API ключ)", lang)
