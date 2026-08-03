"""iMe chat search remains explicitly confirmation-gated in Telegram."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class FakeIMe:
    title = "iMe Messenger"

    def __init__(self):
        self.calls = []

    def open_chat(self, contact, confirm=False):
        self.calls.append((contact, confirm))
        return {"status": "opened"}


def test_ime_chat_open_needs_confirmation(monkeypatch):
    import run_telegram_bot as bot

    fake = FakeIMe()
    monkeypatch.setattr(bot, "_phone_adapter", lambda key: fake)
    api = API()
    chat_id = 808181
    try:
        assert bot._handle_android_phone_workflow_intent(api, chat_id, "открой чат iMe: Иван")
        assert bot._pending_confirm[chat_id]["kind"] == "ime_open_chat"
        assert bot._handle_account_intent(api, chat_id, "да")
        assert fake.calls == [("Иван", True)]
    finally:
        bot._pending_confirm.pop(chat_id, None)
