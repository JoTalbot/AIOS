"""Main AI Advisor Controller — Full Pipeline Integration."""
from __future__ import annotations

import os
from typing import Any

from .compliance_guard import ComplianceGuard
from .intent_classifier import SmartIntentClassifier
from .metrics_collector import MetricsCollector
from .sentiment_analyzer import SentimentAnalyzer
from .templates_engine import AdvisorTemplateIntegration, TemplateEngine


class AIAdvisor:
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        self.template_engine = TemplateEngine(storage_path=templates_dir)
        self.template_integration = AdvisorTemplateIntegration(self.template_engine)
        self.intent_classifier = SmartIntentClassifier(use_llm=use_llm)
        self.compliance_guard = ComplianceGuard()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.metrics = MetricsCollector(storage_path=os.path.join(templates_dir, "metrics"))

    def _calculate_dynamic_price(self, context: dict[str, Any]) -> dict[str, Any]:
        product = context.get("product", {})
        base_price = product.get("price", 0)
        history = context.get("negotiation_history", [])
        
        if len(history) >= 2:
            return {"price": int(base_price * 0.95), "reason": "Лояльность: скидка 5%"}
        if len(history) == 1 and "price_inquiry" in [h.get("intent") for h in history]:
            return {"price": int(base_price * 0.98), "reason": "Микро-скидка 2%"}
        return {"price": base_price, "reason": "Стандартная цена"}

    async def process_incoming_message(self, message_id: str, platform: str,
                                       incoming_text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Полный пайплайн: Sentiment → Intent → Pricing → Template → Compliance."""
        
        # 1. Анализ тональности
        sentiment = self.sentiment_analyzer.analyze(incoming_text, context.get("lang", "uk"))
        self.metrics.record_sentiment(sentiment.sentiment)
        
        # 2. Если негатив — эскалация
        if sentiment.requires_escalation:
            self.metrics.record_escalation()
            return {
                "message_id": message_id, "platform": platform,
                "status": "escalated",
                "sentiment": sentiment.sentiment,
                "escalation_reason": sentiment.reason,
                "requires_human": True
            }
        
        # 3. Классификация намерения (с LLM если нужно)
        intent_result = await self.intent_classifier.classify(incoming_text, context)
        self.metrics.record_intent(intent_result.intent)
        
        # 4. Обогащение контекста (цены, язык)
        enriched_context = {**context}
        if "product" in enriched_context:
            pricing = self._calculate_dynamic_price(enriched_context)
            enriched_context["product"]["suggested_price"] = pricing["price"]
            enriched_context["pricing_reason"] = pricing["reason"]
        enriched_context["lang"] = intent_result.language
        
        # 5. Генерация черновика
        draft_result = self.template_integration.generate_draft_with_template(
            intent=intent_result.intent, platform=platform, context=enriched_context)
        
        if draft_result["status"] != "success":
            return {
                "message_id": message_id, "platform": platform,
                "status": "no_template",
                "intent": intent_result.intent,
                "draft_status": draft_result["status"]
            }
        
        # 6. Проверка на соответствие Конституции
        violations = self.compliance_guard.check(draft_result["rendered_text"], enriched_context)
        if violations:
            self.metrics.record_compliance_violation()
            return {
                "message_id": message_id, "platform": platform,
                "status": "compliance_failed",
                "violations": [{"article": v.article, "message": v.message} for v in violations]
            }
        
        # 7. Успех — черновик готов
        self.metrics.record_draft_created()
        
        return {
            "message_id": message_id, "platform": platform,
            "status": "draft_ready",
            "language": intent_result.language,
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "draft_id": draft_result["draft_id"],
            "draft_text": draft_result["rendered_text"],
            "template_used": draft_result["template_name"],
            "requires_approval": True,
            "sentiment": sentiment.sentiment
        }

# === Интеграция с Platform Registry ===
from aios_core.platforms.registry import PlatformRegistry


class AIAdvisorWithPlatforms(AIAdvisor):
    """AI Advisor с интеграцией платформенных адаптеров."""
    
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        super().__init__(templates_dir, use_llm)
        self.platform_registry = PlatformRegistry()

    def register_platform(self, platform: str, config: dict[str, Any] | None = None):
        """Зарегистрировать платформу."""
        self.platform_registry.register_adapter(platform, config)

    async def process_and_respond(self, platform: str, message_id: str,
                                  incoming_text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Полный цикл: обработка + автоматическая отправка после одобрения."""
        
        # Обработка через основной пайплайн
        result = await self.process_incoming_message(message_id, platform, incoming_text, context)
        
        if result["status"] == "draft_ready":
            # Здесь можно интегрировать с Telegram ботом для одобрения
            # После одобрения — автоматическая отправка через платформу
            pass
        
        return result
