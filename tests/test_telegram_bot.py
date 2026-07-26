"""Tests for Telegram Approval Bot."""
import pytest
from aios_core.advisor.telegram_bot import TelegramApprovalBot

@pytest.mark.asyncio
async def test_send_draft_for_approval():
    """Бот принимает черновик на одобрение."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    draft_id = await bot.send_draft_for_approval({
        "draft_id": "draft_001",
        "platform": "olx",
        "message_id": "msg_001",
        "intent": "price_inquiry",
        "language": "uk",
        "draft_text": "Тестовый черновик"
    })
    assert draft_id == "draft_001"
    assert draft_id in bot.pending_drafts

@pytest.mark.asyncio
async def test_approve_draft():
    """Одобрение черновика."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_002", "platform": "olx",
        "message_id": "msg_002", "intent": "greeting",
        "language": "ru", "draft_text": "Привет!"
    })
    
    result = await bot.approve_draft("draft_002")
    assert result["status"] == "approved"
    assert "draft_002" not in bot.pending_drafts

@pytest.mark.asyncio
async def test_reject_draft():
    """Отклонение черновика."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_003", "platform": "olx",
        "message_id": "msg_003", "intent": "greeting",
        "language": "ru", "draft_text": "Тест"
    })
    
    result = await bot.reject_draft("draft_003", reason="Неверный текст")
    assert result["status"] == "rejected"

@pytest.mark.asyncio
async def test_handle_callback_approve():
    """Обработка callback approve_."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    await bot.send_draft_for_approval({
        "draft_id": "draft_004", "platform": "olx",
        "message_id": "msg_004", "intent": "greeting",
        "language": "ru", "draft_text": "Тест"
    })
    
    result = await bot.handle_callback("approve_draft_004")
    assert result["status"] == "approved"

@pytest.mark.asyncio
async def test_unknown_draft():
    """Ошибка при неизвестном черновике."""
    bot = TelegramApprovalBot(bot_token="test", chat_id="123")
    result = await bot.approve_draft("unknown_id")
    assert result["status"] == "error"
