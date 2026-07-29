"""End-to-end tests for full AI Advisor pipeline."""
import tempfile

import pytest

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
