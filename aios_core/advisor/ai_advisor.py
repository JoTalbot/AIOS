"""Main AI Advisor Controller."""
from __future__ import annotations
from typing import Dict, Any, Optional
from .templates_engine import TemplateEngine, AdvisorTemplateIntegration
from .intent_classifier import SmartIntentClassifier

class AIAdvisor:
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        self.template_engine = TemplateEngine(storage_path=templates_dir)
        self.template_integration = AdvisorTemplateIntegration(self.template_engine)
        self.intent_classifier = SmartIntentClassifier(use_llm=use_llm)

    async def process_incoming_message(
        self,
        message_id: str,
        platform: str,
        incoming_text: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Полный цикл обработки входящего сообщения."""
        
        intent_result = self.intent_classifier.classify(incoming_text, context)
        
        draft_result = self.template_integration.generate_draft_with_template(
            intent=intent_result.intent,
            platform=platform,
            context=context,
            template_id=None
        )
        
        return {
            "message_id": message_id,
            "platform": platform,
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "intent_reasoning": intent_result.reasoning,
            "draft_status": draft_result["status"],
            "draft_text": draft_result.get("rendered_text", ""),
            "requires_approval": True,
            "template_used": draft_result.get("template_name", "None")
        }
