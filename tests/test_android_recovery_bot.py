"""Telegram recovery intent produces an actionable metadata-only result."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_recovery_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.android_recovery as recovery

    class Recovery:
        def __init__(self, root): pass
        def check(self): return {"action": "none"}

    monkeypatch.setattr(recovery, "AndroidRecovery", Recovery)
    api = API()
    assert bot._handle_phone_recovery_intent(api, 1, "восстановление телефона")
    assert "работают штатно" in str(api.messages[-1][0][1])
