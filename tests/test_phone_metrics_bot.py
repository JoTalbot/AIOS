"""Telegram metrics intent only renders aggregate changes."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))
    def send_document(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_metrics_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_metrics as metrics

    class Store:
        def __init__(self, root): pass
        def trend(self, limit=7): return {"snapshots": 2, "changes": {"leads_pending": 1, "crm_open": 0, "bank_tasks": 0, "apps_calibrated": 0}}
        def availability(self, limit=30): return {"adb_pct": 100, "companion_pct": 100}

    monkeypatch.setattr(metrics, "PhoneMetricsStore", Store)
    api = API()
    assert bot._handle_phone_metrics_intent(api, 10, "тренды телефона")
    assert "Тренды телефона" in str(api.messages[-1][0][1])
