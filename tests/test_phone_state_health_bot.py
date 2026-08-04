"""Telegram state health command remains metadata-only."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_state_health_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_state_health as state

    class Health:
        def __init__(self, root): pass
        def snapshot(self): return {"status": "ok", "wireguard_active": True, "backup_age_hours": 1, "files": [{}], "invalid": [], "total_bytes": 7}

    monkeypatch.setattr(state, "PhoneStateHealth", Health)
    api = API()
    assert bot._handle_phone_recovery_intent(api, 1, "здоровье данных телефона")
    assert "Состояние данных телефона" in str(api.messages[-1][0][1])
