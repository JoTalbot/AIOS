"""Smart Intent Classifier for AI Advisor."""
from __future__ import annotations
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    confidence: float
    reasoning: str

class SmartIntentClassifier:
    """Гибридный классификатор намерений (Эвристика + LLM fallback)."""
    
    def __init__(self, use_llm: bool = False, llm_model: str = "gpt-3.5-turbo"):
        self.use_llm = use_llm
        self.llm_model = llm_model
        self.keyword_map = {
            "price_inquiry": ["цена", "сколько стоит", "последняя цена", "торг", "дешевле", "скидка"],
            "delivery_question": ["доставка", "новая почта", "укрпочта", "отправите", "самовывоз"],
            "stock_check": ["в наличии", "осталось", "есть ли", "резерв"],
            "greeting": ["здравствуйте", "добрый день", "привет", "доброго времени"],
            "complaint": ["брак", "не работает", "возврат", "обман", "жалоба"]
        }

    def classify(self, message: str, context: Optional[Dict] = None) -> IntentResult:
        message_lower = message.lower()
        
        best_intent = "unknown"
        max_matches = 0
        
        for intent, keywords in self.keyword_map.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > max_matches:
                max_matches = matches
                best_intent = intent
                
        if max_matches >= 1:
            confidence = min(0.7 + (max_matches * 0.1), 0.95)
            return IntentResult(
                intent=best_intent, 
                confidence=confidence, 
                reasoning=f"Найдено {max_matches} ключевых слов для '{best_intent}'"
            )
            
        if self.use_llm:
            return self._classify_with_llm(message, context)
            
        return IntentResult(intent="general_inquiry", confidence=0.5, reasoning="Эвристика не сработала, LLM отключен")

    def _classify_with_llm(self, message: str, context: Optional[Dict]) -> IntentResult:
        return IntentResult(
            intent="general_inquiry", 
            confidence=0.6, 
            reasoning="LLM анализ (заглушка)"
        )
