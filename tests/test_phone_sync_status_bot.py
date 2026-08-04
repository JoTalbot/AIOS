"""Telegram sync status stays metadata-only."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_sync_status_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_sync_status as sync

    class Status:
        def __init__(self, root): pass
        def snapshot(self): return {"fresh": 1, "total": 1, "sources": [{"id": "lead_sync", "exists": True, "age_minutes": 2}]}

    monkeypatch.setattr(sync, "PhoneSyncStatus", Status)
    api = API()
    assert bot._handle_phone_recovery_intent(api, 1, "статус синхронизации телефона")
    assert "Синхронизации телефона" in str(api.messages[-1][0][1])
