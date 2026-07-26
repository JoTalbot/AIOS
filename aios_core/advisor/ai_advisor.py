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
