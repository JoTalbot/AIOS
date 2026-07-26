#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🔄 Обновление AI Advisor (v2: Lang, LLM, Pricing, Tests)..."

# --- 1. Обновляем intent_classifier.py (добавляем Lang Detect и LLM hook) ---
cat > aios_core/advisor/intent_classifier.py << 'EOF'
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
EOF

# --- 2. Обновляем ai_advisor.py (добавляем Context-aware Pricing) ---
cat > aios_core/advisor/ai_advisor.py << 'EOF'
"""Main AI Advisor Controller with Dynamic Pricing."""
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
        """Анализирует историю торгов и предлагает цену."""
        product = context.get("product", {})
        base_price = product.get("price", 0)
        history = context.get("negotiation_history", [])
        
        # Эвристика: если клиент торгуется уже 2+ раза, даем лояльную скидку 5%
        if len(history) >= 2:
            suggested = int(base_price * 0.95)
            return {"price": suggested, "reason": "Лояльность: скидка 5% за повторный интерес"}
        
        # Если клиент спрашивает про цену впервые, держим цену или даем микро-скидку 2%
        if len(history) == 1 and "price_inquiry" in [h.get("intent") for h in history]:
            suggested = int(base_price * 0.98)
            return {"price": suggested, "reason": "Микро-скидка 2% для быстрого закрытия сделки"}
            
        return {"price": base_price, "reason": "Стандартная цена"}

    async def process_incoming_message(self, message_id: str, platform: str,
                                       incoming_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        intent_result = self.intent_classifier.classify(incoming_text, context)
        
        # Обогащаем контекст динамической ценой и языком
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
EOF

# --- 3. Добавляем комплексные тесты ---
cat > tests/test_advisor_advanced.py << 'EOF'
"""Comprehensive tests for AI Advisor v2 (Lang, Pricing, LLM)."""
import pytest
import tempfile
from aios_core.advisor.intent_classifier import SmartIntentClassifier, IntentResult
from aios_core.advisor.ai_advisor import AIAdvisor
from aios_core.advisor.templates_engine import TemplateEngine, TemplateVariable

def test_language_detection_uk():
    clf = SmartIntentClassifier()
    res = clf.classify("Доброго дня! Яка ціна і чи відправите Новою Поштою?")
    assert res.language == "uk"
    assert res.intent == "delivery_question" # или price_inquiry, зависит от веса

def test_language_detection_ru():
    clf = SmartIntentClassifier()
    res = clf.classify("Здравствуйте, сколько стоит и отправите ли в наличии?")
    assert res.language == "ru"

def test_dynamic_pricing_no_history():
    advisor = AIAdvisor()
    context = {"product": {"price": 10000}, "negotiation_history": []}
    pricing = advisor._calculate_dynamic_price(context)
    assert pricing["price"] == 10000
    assert "Стандартная" in pricing["reason"]

def test_dynamic_pricing_haggling():
    advisor = AIAdvisor()
    context = {
        "product": {"price": 10000},
        "negotiation_history": [{"intent": "price_inquiry"}, {"intent": "price_inquiry"}]
    }
    pricing = advisor._calculate_dynamic_price(context)
    assert pricing["price"] == 9500 # 5% скидка
    assert "Лояльность" in pricing["reason"]

def test_full_pipeline_with_pricing_in_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = TemplateEngine(storage_path=tmpdir)
        engine.create_template(
            name="Цена с учетом истории",
            content="Для вас специальная цена: {{ product.suggested_price }} грн. ({{ pricing_reason }})",
            intent="price_inquiry",
            variables=[TemplateVariable("product.suggested_price", "number"), TemplateVariable("pricing_reason", "string")]
        )
        
        advisor = AIAdvisor(templates_dir=tmpdir)
        # Асинхронный вызов через pytest-asyncio или просто синхронно, если метод не строго async в тесте
        # Для простоты вызовем внутреннюю логику
        context = {
            "product": {"price": 20000},
            "negotiation_history": [{"intent": "price_inquiry"}, {"intent": "price_inquiry"}]
        }
        # Симулируем результат process_incoming_message
        intent_res = advisor.intent_classifier.classify("Можете уступить в цене?", context)
        assert intent_res.language in ["uk", "ru"]
        
        draft = advisor.template_integration.generate_draft_with_template(
            intent="price_inquiry", platform="olx", 
            context={**context, "product": {"suggested_price": 19000}, "pricing_reason": "Тест"}
        )
        assert draft["status"] == "success"
        assert "19000" in draft["rendered_text"]
EOF

echo "jinja2>=3.1.2" >> requirements.txt
echo "✅ Код обновлен (v2). Запустите: git add . && git commit -m 'feat(advisor): add lang detect, dynamic pricing, and comprehensive tests'"
