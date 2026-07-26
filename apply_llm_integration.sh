#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🔄 Обновление AI Advisor: реальная LLM-интеграция..."

# 1. Добавляем httpx в зависимости (если еще нет)
if ! grep -q "httpx" requirements.txt 2>/dev/null; then
    echo "httpx>=0.27.0" >> requirements.txt
    echo "✅ Добавлено: httpx>=0.27.0"
fi

# 2. Обновляем intent_classifier.py с реальной LLM-логикой
cat > aios_core/advisor/intent_classifier.py << 'PYEOF'
"""Smart Intent Classifier with Real LLM Integration."""
from __future__ import annotations
import os
import json
import httpx
from typing import Dict, Optional
from dataclasses import dataclass

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

    async def classify(self, message: str, context: Optional[Dict] = None) -> IntentResult:
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
            return IntentResult("general_inquiry", 0.5, f"LLM error: {str(e)}", lang)
PYEOF

# 3. Обновляем ai_advisor.py (добавляем await к classify)
cat > aios_core/advisor/ai_advisor.py << 'PYEOF'
"""Main AI Advisor Controller with Dynamic Pricing and Async LLM."""
from __future__ import annotations
from typing import Dict, Any
from .templates_engine import TemplateEngine, AdvisorTemplateIntegration
from .intent_classifier import SmartIntentClassifier

class AIAdvisor:
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        self.template_engine = TemplateEngine(storage_path=templates_dir)
        self.template_integration = AdvisorTemplateIntegration(self.template_engine)
        self.intent_classifier = SmartIntentClassifier(use_llm=use_llm)

    def _calculate_dynamic_price(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product = context.get("product", {})
        base_price = product.get("price", 0)
        history = context.get("negotiation_history", [])
        
        if len(history) >= 2:
            return {"price": int(base_price * 0.95), "reason": "Лояльность: скидка 5% за повторный интерес"}
        if len(history) == 1 and "price_inquiry" in [h.get("intent") for h in history]:
            return {"price": int(base_price * 0.98), "reason": "Микро-скидка 2% для быстрого закрытия"}
        return {"price": base_price, "reason": "Стандартная цена"}

    async def process_incoming_message(self, message_id: str, platform: str,
                                       incoming_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Теперь classify асинхронный
        intent_result = await self.intent_classifier.classify(incoming_text, context)
        
        enriched_context = {**context}
        if "product" in enriched_context:
            pricing = self._calculate_dynamic_price(enriched_context)
            enriched_context["product"]["suggested_price"] = pricing["price"]
            enriched_context["pricing_reason"] = pricing["reason"]
        enriched_context["lang"] = intent_result.language

        draft_result = self.template_integration.generate_draft_with_template(
            intent=intent_result.intent, platform=platform, context=enriched_context)
            
        return {
            "message_id": message_id, "platform": platform,
            "language": intent_result.language,
            "intent": intent_result.intent, "intent_confidence": intent_result.confidence,
            "draft_status": draft_result["status"],
            "draft_text": draft_result.get("rendered_text", ""),
            "requires_approval": True,
            "template_used": draft_result.get("template_name", "None"),
        }
PYEOF

echo "✅ LLM-интеграция применена!"
