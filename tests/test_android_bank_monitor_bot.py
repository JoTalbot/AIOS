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


def test_bank_task_review_needs_confirmation(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.android_bank_monitor as monitor

    class BankMonitor:
        def __init__(self, root): pass
        def list_tasks(self, limit=30): return [{"id": "bank-1", "source": "A-Bank", "observed_at": "2026-08-04T10:00:00", "age_state": "fresh"}]
        def task_summary(self): return {"pending": 1, "attention": 0, "overdue": 0}
        def review_task(self, task_id):
            self.reviewed = task_id
            return {"status": "reviewed"}

    instance = BankMonitor(None)
    monkeypatch.setattr(monitor, "AndroidBankMonitor", lambda root: instance)
    api = API()
    chat_id = 66
    try:
        assert bot._handle_phone_bank_monitor_intent(api, chat_id, "банковские задачи телефона")
        assert bot._handle_phone_bank_monitor_intent(api, chat_id, "отметь банковскую задачу 1 обработанной")
        pending = bot._pending_confirm.pop(chat_id)
        assert pending["kind"] == "bank_task_review"
        assert bot._confirm_phone_pending(api, chat_id, pending["kind"], pending["data"])
        assert instance.reviewed == "bank-1"
    finally:
        bot._last_bank_tasks.pop(chat_id, None)
        bot._pending_confirm.pop(chat_id, None)
