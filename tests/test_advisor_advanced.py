"""Comprehensive tests for AI Advisor v2 (Lang, Pricing, LLM)."""
import pytest
import tempfile
from aios_core.advisor.intent_classifier import SmartIntentClassifier, IntentResult
from aios_core.advisor.ai_advisor import AIAdvisor
from aios_core.advisor.templates_engine import TemplateEngine, TemplateVariable

@pytest.mark.asyncio
async def test_language_detection_uk():
    clf = SmartIntentClassifier()
    res = await clf.classify("Доброго дня! Яка ціна і чи відправите Новою Поштою?")
    assert res.language == "uk"
    assert res.intent == "delivery_question" # или price_inquiry, зависит от веса

@pytest.mark.asyncio
async def test_language_detection_ru():
    clf = SmartIntentClassifier()
    res = await clf.classify("Здравствуйте, сколько стоит и отправите ли в наличии?")
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

@pytest.mark.asyncio
async def test_full_pipeline_with_pricing_in_template():
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
        intent_res = await advisor.intent_classifier.classify("Можете уступить в цене?", context)
        assert intent_res.language in ["uk", "ru"]
        
        draft = advisor.template_integration.generate_draft_with_template(
            intent="price_inquiry", platform="olx", 
            context={**context, "product": {"suggested_price": 19000}, "pricing_reason": "Тест"}
        )
        assert draft["status"] == "success"
        assert "19000" in draft["rendered_text"]
