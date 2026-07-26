#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🚀 Применяю полное обновление AI Advisor (v3: Pipeline, Metrics, Telegram, Docker)..."

# === 1. Обновляем ai_advisor.py — единый пайплайн ===
cat > aios_core/advisor/ai_advisor.py << 'PYEOF'
"""Main AI Advisor Controller — Full Pipeline Integration."""
from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
from .templates_engine import TemplateEngine, AdvisorTemplateIntegration
from .intent_classifier import SmartIntentClassifier
from .compliance_guard import ComplianceGuard
from .sentiment_analyzer import SentimentAnalyzer
from .metrics_collector import MetricsCollector

class AIAdvisor:
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        self.template_engine = TemplateEngine(storage_path=templates_dir)
        self.template_integration = AdvisorTemplateIntegration(self.template_engine)
        self.intent_classifier = SmartIntentClassifier(use_llm=use_llm)
        self.compliance_guard = ComplianceGuard()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.metrics = MetricsCollector()

    def _calculate_dynamic_price(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product = context.get("product", {})
        base_price = product.get("price", 0)
        history = context.get("negotiation_history", [])
        
        if len(history) >= 2:
            return {"price": int(base_price * 0.95), "reason": "Лояльность: скидка 5%"}
        if len(history) == 1 and "price_inquiry" in [h.get("intent") for h in history]:
            return {"price": int(base_price * 0.98), "reason": "Микро-скидка 2%"}
        return {"price": base_price, "reason": "Стандартная цена"}

    async def process_incoming_message(self, message_id: str, platform: str,
                                       incoming_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
PYEOF

# === 2. Создаём Metrics Collector ===
cat > aios_core/advisor/metrics_collector.py << 'PYEOF'
"""Metrics Collector — сбор статистики работы AI Advisor."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class MetricsCollector:
    def __init__(self, storage_path: str = "data/metrics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_date = datetime.utcnow().strftime("%Y-%m-%d")
        self.metrics_file = self.storage_path / f"{self.current_date}.json"
        self._load()

    def _load(self):
        if self.metrics_file.exists():
            self.data = json.loads(self.metrics_file.read_text())
        else:
            self.data = {
                "date": self.current_date,
                "drafts_created": 0,
                "drafts_approved": 0,
                "drafts_rejected": 0,
                "escalations": 0,
                "compliance_violations": 0,
                "intents": {},
                "sentiments": {"positive": 0, "neutral": 0, "negative": 0},
                "platforms": {}
            }

    def _save(self):
        self.metrics_file.write_text(json.dumps(self.data, indent=2))

    def record_draft_created(self):
        self.data["drafts_created"] += 1
        self._save()

    def record_draft_approved(self):
        self.data["drafts_approved"] += 1
        self._save()

    def record_draft_rejected(self):
        self.data["drafts_rejected"] += 1
        self._save()

    def record_escalation(self):
        self.data["escalations"] += 1
        self._save()

    def record_compliance_violation(self):
        self.data["compliance_violations"] += 1
        self._save()

    def record_intent(self, intent: str):
        self.data["intents"][intent] = self.data["intents"].get(intent, 0) + 1
        self._save()

    def record_sentiment(self, sentiment: str):
        self.data["sentiments"][sentiment] = self.data["sentiments"].get(sentiment, 0) + 1
        self._save()

    def record_platform(self, platform: str):
        self.data["platforms"][platform] = self.data["platforms"].get(platform, 0) + 1
        self._save()

    def get_summary(self) -> Dict[str, Any]:
        total_drafts = self.data["drafts_created"]
        approval_rate = (self.data["drafts_approved"] / total_drafts * 100) if total_drafts > 0 else 0
        return {
            "date": self.data["date"],
            "drafts_created": total_drafts,
            "approval_rate": f"{approval_rate:.1f}%",
            "escalations": self.data["escalations"],
            "compliance_violations": self.data["compliance_violations"],
            "top_intents": sorted(self.data["intents"].items(), key=lambda x: x[1], reverse=True)[:5],
            "sentiment_distribution": self.data["sentiments"]
        }
PYEOF

# === 3. Создаём Telegram Bot ===
cat > aios_core/advisor/telegram_bot.py << 'PYEOF'
"""Telegram Bot for Manager Approval of Drafts."""
from __future__ import annotations
import os
import json
from typing import Dict, Any
from pathlib import Path

class TelegramApprovalBot:
    """Бот для одобрения черновиков через Telegram."""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.pending_drafts: Dict[str, Dict[str, Any]] = {}

    async def send_draft_for_approval(self, draft_data: Dict[str, Any]) -> str:
        """Отправить черновик менеджеру на одобрение."""
        draft_id = draft_data["draft_id"]
        self.pending_drafts[draft_id] = draft_data
        
        message = (
            f"🤖 Новый черновик ответа\n\n"
            f"📱 Платформа: {draft_data['platform']}\n"
            f"🎯 Намерение: {draft_data['intent']}\n"
            f"🌍 Язык: {draft_data['language']}\n\n"
            f"📝 Текст:\n{draft_data['draft_text']}\n\n"
            f"✅ Одобрить: /approve_{draft_id}\n"
            f"❌ Отклонить: /reject_{draft_id}"
        )
        
        # TODO: Реальный вызов Telegram API
        # await self._send_telegram_message(message)
        
        return draft_id

    async def approve_draft(self, draft_id: str) -> Dict[str, Any]:
        """Одобрить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        draft["status"] = "approved"
        
        # TODO: Отправить одобренный текст через Platform Adapter
        # await platform_adapter.send_message(draft["platform"], draft["message_id"], draft["draft_text"])
        
        return {"status": "approved", "draft_id": draft_id}

    async def reject_draft(self, draft_id: str, reason: str = "") -> Dict[str, Any]:
        """Отклонить черновик."""
        if draft_id not in self.pending_drafts:
            return {"status": "error", "message": "Черновик не найден"}
        
        draft = self.pending_drafts.pop(draft_id)
        draft["status"] = "rejected"
        draft["rejection_reason"] = reason
        
        return {"status": "rejected", "draft_id": draft_id}
PYEOF

# === 4. Создаём E2E тесты ===
cat > tests/test_e2e_pipeline.py << 'PYEOF'
"""End-to-end tests for full AI Advisor pipeline."""
import pytest
import tempfile
from aios_core.advisor.ai_advisor import AIAdvisor
from aios_core.advisor.templates_engine import TemplateVariable

@pytest.fixture
def advisor():
    with tempfile.TemporaryDirectory() as tmpdir:
        adv = AIAdvisor(templates_dir=tmpdir, use_llm=False)
        # Создаём тестовые шаблоны
        adv.template_engine.create_template(
            name="Цена",
            content="Цена: {{ product.suggested_price }} грн ({{ pricing_reason }})",
            intent="price_inquiry",
            variables=[
                TemplateVariable("product.suggested_price", "number"),
                TemplateVariable("pricing_reason", "string")
            ]
        )
        yield adv

@pytest.mark.asyncio
async def test_full_pipeline_happy_path(advisor):
    """Полный пайплайн без проблем."""
    result = await advisor.process_incoming_message(
        message_id="msg_001",
        platform="olx",
        incoming_text="Здравствуйте, какая цена?",
        context={
            "lang": "ru",
            "product": {"price": 10000},
            "negotiation_history": []
        }
    )
    
    assert result["status"] == "draft_ready"
    assert result["intent"] == "price_inquiry"
    assert "draft_text" in result
    assert result["requires_approval"] is True

@pytest.mark.asyncio
async def test_pipeline_with_negative_sentiment(advisor):
    """Негативное сообщение → эскалация."""
    result = await advisor.process_incoming_message(
        message_id="msg_002",
        platform="olx",
        incoming_text="Это обман! Хочу возврат!",
        context={"lang": "ru"}
    )
    
    assert result["status"] == "escalated"
    assert result["requires_human"] is True

@pytest.mark.asyncio
async def test_pipeline_with_compliance_violation(advisor):
    """Черновик нарушает Конституцию."""
    # Создаём шаблон с нарушением
    advisor.template_engine.create_template(
        name="Гарантия",
        content="Гарантируем 100% оригинал!",
        intent="greeting",
        variables=[]
    )
    
    result = await advisor.process_incoming_message(
        message_id="msg_003",
        platform="olx",
        incoming_text="Здравствуйте",
        context={"lang": "ru"}
    )
    
    assert result["status"] == "compliance_failed"
    assert "violations" in result

@pytest.mark.asyncio
async def test_pipeline_with_dynamic_pricing(advisor):
    """Динамическая цена на основе истории торгов."""
    result = await advisor.process_incoming_message(
        message_id="msg_004",
        platform="olx",
        incoming_text="Можете уступить?",
        context={
            "lang": "ru",
            "product": {"price": 20000},
            "negotiation_history": [
                {"intent": "price_inquiry"},
                {"intent": "price_inquiry"}
            ]
        }
    )
    
    assert result["status"] == "draft_ready"
    assert "19000" in result["draft_text"]  # 5% скидка

def test_metrics_collection(advisor):
    """Сбор метрик работает."""
    advisor.metrics.record_draft_created()
    advisor.metrics.record_draft_approved()
    advisor.metrics.record_intent("price_inquiry")
    advisor.metrics.record_sentiment("neutral")
    
    summary = advisor.metrics.get_summary()
    assert summary["drafts_created"] == 1
    assert summary["approval_rate"] == "100.0%"
PYEOF

# === 5. Создаём Docker Compose ===
cat > docker-compose.yml << 'YAMLEOF'
version: '3.8'

services:
  aios-core:
    build: .
    ports:
      - "8080:8080"
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL:-https://api.openai.com/v1}
      - LLM_MODEL=${LLM_MODEL:-gpt-3.5-turbo}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    volumes:
      - ./data:/app/data
      - ./aios_core:/app/aios_core
    restart: unless-stopped

  # Опционально: локальный LLM через Ollama
  # ollama:
  #   image: ollama/ollama
  #   ports:
  #     - "11434:11434"
  #   volumes:
  #     - ollama_data:/root/.ollama

volumes:
  ollama_data:
YAMLEOF

# === 6. Обновляем requirements.txt ===
cat >> requirements.txt << 'REQEOF'
httpx>=0.27.0
python-telegram-bot>=20.0
pytest-asyncio>=0.21.0
REQEOF

# === 7. Создаём пример .env ===
cat > .env.example << 'ENVEOF'
# LLM Configuration
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Telegram Bot (для одобрения черновиков)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Для локального Ollama (альтернатива OpenAI):
# LLM_API_KEY=ollama
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL=llama3
ENVEOF

echo "✅ Все модули применены!"
