"""Telegram route for the phone control center."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


def test_control_center_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_control_center as center

    class Center:
        def __init__(self, root): pass
        def snapshot(self):
            return {
                "status": "ok", "issues": [],
                "device": {"connected": True, "companion": True},
                "apps": [], "leads": {}, "audit": {}, "timers": {},
            }

    monkeypatch.setattr(center, "PhoneControlCenter", Center)
    api = API()
    assert bot._handle_phone_control_center_intent(api, 123, "центр телефона")
    assert "ЦЕНТР УПРАВЛЕНИЯ" in str(api.messages[-1][0][1])
