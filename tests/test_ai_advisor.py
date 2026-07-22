"""AI Advisor H3.11 tests"""

from aios_core.ai_advisor import AISalesAdvisor, TemplateRegistry

def test_template_registry():
    reg = TemplateRegistry()
    tmpl = reg.get("olx", "greeting")
    assert "Добрый" in tmpl or "Спасибо" in tmpl or len(tmpl) > 0
    rendered = reg.render("olx", "default", original="test", context="по товару")
    assert "test" in rendered or "товар" in rendered

def test_draft_reply_default():
    advisor = AISalesAdvisor()
    draft = advisor.draft_reply(
        platform="olx",
        original_message="Какая цена?",
        recipient="buyer123",
        item_context={"title": "iPhone 13", "price": 22000}
    )
    assert draft.platform == "olx"
    assert draft.recipient == "buyer123"
    assert len(draft.draft_reply) > 10
    assert draft.requires_approval is True
    assert draft.confidence > 0

def test_draft_price_negotiation():
    advisor = AISalesAdvisor()
    draft = advisor.draft_reply(
        platform="olx",
        original_message="Торг уместен? Предлагаю 18000",
        recipient="buyer456",
        item_context={"title": "iPhone 13", "price": 22000, "id": "123"}
    )
    assert draft.suggested_price is not None or "грн" in draft.draft_reply

def test_inbox_summary():
    advisor = AISalesAdvisor()
    summary = advisor.summarize_inbox("olx", [
        {"sender": "user1", "text": "Привет, есть в наличии?", "read": False},
        {"sender": "user2", "text": "Куплю сегодня, срочно!", "read": False},
        {"sender": "user1", "text": "Спасибо!", "read": True},
    ])
    assert summary.total_messages == 3
    assert summary.unread == 2
    assert len(summary.urgent) >= 1

def test_price_advice():
    advisor = AISalesAdvisor()
    advice = advisor.price_advice("olx", "item_123", 25000, market_samples=[20000, 21000, 22000])
    assert advice.suggested_price < 25000
    assert advice.confidence > 0
    assert "рынка" in advice.reason or len(advice.reason) > 10

def test_draft_approval_flow():
    advisor = AISalesAdvisor()
    draft = advisor.draft_reply("olx", "Здравствуйте", "buyer", {"title": "Test"})
    assert advisor.get_draft(draft.id) is not None
    advisor.approve_draft(draft.id, "operator")
    assert advisor.get_draft(draft.id).requires_approval is False

def test_list_drafts():
    advisor = AISalesAdvisor()
    advisor.draft_reply("olx", "Test 1", "a", {})
    advisor.draft_reply("olx", "Test 2", "b", {})
    assert len(advisor.list_drafts()) == 2
