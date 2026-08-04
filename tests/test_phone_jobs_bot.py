"""Telegram job status command only reports scheduler metadata."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_jobs_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_jobs as jobs

    class Jobs:
        def __init__(self, root): pass
        def snapshot(self): return {"status": "ok", "active": 2, "total": 2, "backup": {"count": 1, "retention_ok": True, "invalid": 0}}
        def dry_run(self): return {"status": "ok", "jobs": [{"valid": True}]}

    monkeypatch.setattr(jobs, "PhoneJobs", Jobs)
    api = API()
    assert bot._handle_phone_jobs_intent(api, 1, "планировщик телефона")
    assert "Планировщик телефона" in str(api.messages[-1][0][1])
