"""Tests for the metadata-only weekly phone/CRM report."""
from __future__ import annotations

import json
from datetime import datetime, timezone


def test_weekly_report_contains_counts_not_payloads(monkeypatch, tmp_path):
    import run_phone_weekly_report as report

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat()
    (data / "lead_candidates.json").write_text(json.dumps([
        {"id": "a", "created_at": now, "status": "pending_review", "source": "WhatsApp"},
    ]), encoding="utf-8")
    (data / "crm_followup_tasks.json").write_text(json.dumps([
        {"id": "t", "created_at": now, "status": "open", "source": "WhatsApp"},
    ]), encoding="utf-8")

    class Center:
        def __init__(self, root): pass
        def snapshot(self):
            return {"device": {"connected": True, "companion": True}}

    monkeypatch.setattr(report, "PhoneControlCenter", Center)
    text = report.build_text(tmp_path, days=7)
    assert "новые 1" in text
    assert "CRM follow-up" in text
    assert "секрет" not in text


def test_weekly_report_bot_command(monkeypatch):
    import run_telegram_bot as bot
    import run_phone_weekly_report as report

    monkeypatch.setattr(report, "build_text", lambda root, days=7: "📊 <b>Недельный тест</b>")

    class API:
        def __init__(self): self.messages = []
        def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))

    api = API()
    assert bot._handle_phone_weekly_report_intent(api, 77, "недельный отчёт телефона")
    assert "Недельный тест" in str(api.messages[-1][0][1])
