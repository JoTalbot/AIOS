"""Telegram workflow readiness command performs no action."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_workflow_readiness_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_workflow_readiness as readiness

    class Ready:
        def __init__(self, root): pass
        def snapshot(self): return {"workflows": [], "ready": 0, "total": 4}

    monkeypatch.setattr(readiness, "PhoneWorkflowReadiness", Ready)
    api = API()
    assert bot._handle_phone_workflow_readiness_intent(api, 1, "проверка сценариев телефона")
    assert "ПРОВЕРКА СЦЕНАРИЕВ" in str(api.messages[-1][0][1])
