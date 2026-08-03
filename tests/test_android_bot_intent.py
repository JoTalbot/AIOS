"""Тесты безопасных Telegram-команд Android Gateway."""
from __future__ import annotations


def test_android_status_intent_uses_gateway(monkeypatch):
    import run_telegram_bot as bot

    monkeypatch.setattr(bot, "_android_gateway_run", lambda args, timeout=60: {
        "status": "ok", "connected": True, "name": "Phone", "android": "15",
        "battery": 80, "screen": "1080x2400", "packages": 100,
    })

    class API:
        def __init__(self): self.messages = []
        def send_message(self, *args, **kwargs): self.messages.append(args)

    api = API()
    assert bot._handle_android_gateway_intent(api, 5, "статус телефона") is True
    assert any("Android Device Adapter" in str(item) for item in api.messages)


def test_android_open_requires_confirmation():
    import run_telegram_bot as bot

    class API:
        def __init__(self): self.messages = []
        def send_message(self, *args, **kwargs): self.messages.append(args)

    chat_id = 1234567
    api = API()
    assert bot._handle_android_gateway_intent(api, chat_id, "открой на телефоне com.android.settings") is True
    assert bot._pending_confirm[chat_id]["kind"] == "android_open_app"
    bot._pending_confirm.pop(chat_id, None)
