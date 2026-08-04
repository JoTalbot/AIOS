"""Telegram bank monitor intent remains metadata-only."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_bank_monitor_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.android_bank_monitor as monitor

    class BankMonitor:
        def __init__(self, root): pass
        def snapshot(self):
            return {"banks": [{"title": "A-Bank", "available": True, "unread_notifications": 0}]}

    monkeypatch.setattr(monitor, "AndroidBankMonitor", BankMonitor)
    api = API()
    assert bot._handle_phone_bank_monitor_intent(api, 1, "статус банков телефона")
    text = str(api.messages[-1][0][1])
    assert "A-Bank" in text
    assert "Баланс" in text  # explicit policy text, not an amount
