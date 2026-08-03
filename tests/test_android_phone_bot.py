"""Тесты Telegram-маршрутов для confirmation-gated Android workflows."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class FakeWhatsApp:
    title = "WhatsApp"

    def __init__(self):
        self.calls = []

    def status(self):
        return {"status": "ok", "title": self.title, "available": True,
                "accessibility": True, "active": True, "ui_ready": True}

    def open(self, confirm=False):
        self.calls.append(("open", confirm))
        return {"status": "ok"}

    def open_chat(self, contact, confirm=False):
        self.calls.append(("chat", contact, confirm))
        return {"status": "opened"}

    def prepare_draft(self, text, confirm=False):
        self.calls.append(("draft", text, confirm))
        return {"status": "draft_ready", "draft_id": "draft-1"}

    def send_draft(self, draft_id, confirm=False):
        self.calls.append(("send", draft_id, confirm))
        return {"status": "send_tapped"}

    def cancel_draft(self, draft_id):
        self.calls.append(("cancel", draft_id))
        return {"status": "cancelled"}

    def read_visible_chat(self):
        return {"status": "ok", "messages": ["Привет [код скрыт]"]}


def test_live_android_notification_mask_hides_codes_and_cards():
    import run_telegram_bot as bot

    masked = bot._mask_android_notification("код 123456, карта 4444 3333 2222 1111")
    assert "123456" not in masked
    assert "4444" not in masked


def test_whatsapp_chat_open_is_confirmed(monkeypatch):
    import run_telegram_bot as bot

    fake = FakeWhatsApp()
    monkeypatch.setattr(bot, "_phone_adapter", lambda key: fake)
    api = API()
    chat_id = 987654
    try:
        assert bot._handle_android_phone_workflow_intent(api, chat_id, "открой чат WhatsApp: Иван")
        assert bot._pending_confirm[chat_id]["kind"] == "whatsapp_open_chat"
        assert bot._handle_account_intent(api, chat_id, "да")
        assert ("chat", "Иван", True) in fake.calls
        assert chat_id not in bot._pending_confirm
    finally:
        bot._pending_confirm.pop(chat_id, None)


def test_whatsapp_draft_needs_second_confirmation_and_can_be_cancelled(monkeypatch):
    import run_telegram_bot as bot

    fake = FakeWhatsApp()
    monkeypatch.setattr(bot, "_phone_adapter", lambda key: fake)
    api = API()
    chat_id = 987655
    try:
        assert bot._handle_android_phone_workflow_intent(api, chat_id, "WhatsApp черновик: привет")
        assert bot._pending_confirm[chat_id]["kind"] == "whatsapp_draft"
        assert bot._handle_account_intent(api, chat_id, "да")
        assert bot._pending_confirm[chat_id]["kind"] == "whatsapp_send_draft"
        assert ("draft", "привет", True) in fake.calls
        assert bot._handle_account_intent(api, chat_id, "нет")
        assert ("cancel", "draft-1") in fake.calls
    finally:
        bot._pending_confirm.pop(chat_id, None)
