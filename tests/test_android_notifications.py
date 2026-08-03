"""Тесты безопасного Android notification collector."""
from __future__ import annotations

import json


def test_collector_masks_codes_and_deduplicates(monkeypatch, tmp_path):
    import run_android_notification_collector as collector

    monkeypatch.setattr(collector, "ROOT", tmp_path)
    monkeypatch.setattr(collector, "DATA", tmp_path / "data" / "android_gateway" / "notifications.json")
    monkeypatch.setattr(collector, "STATE", tmp_path / "data" / "android_gateway" / "notification_alerts_state.json")

    class FakeGateway:
        def __init__(self, root): pass
        def notifications(self, limit=50):
            return {"status": "ok", "notifications": [{
                "package": "ua.com.abank", "title": "Код 123456", "text": "OTP 654321", "posted_at": 1,
            }]}

    monkeypatch.setattr(collector, "AndroidGateway", FakeGateway)
    first = collector.collect()
    second = collector.collect()
    assert first["added"] == 1
    assert second["added"] == 0
    items = json.loads(collector.DATA.read_text())
    assert "123456" not in items[0]["title"]
    assert "654321" not in items[0]["text"]


def test_mark_read_updates_android_events(monkeypatch, tmp_path):
    import run_android_notification_collector as collector

    path = tmp_path / "notifications.json"
    monkeypatch.setattr(collector, "DATA", path)
    collector._write(path, [{"id": "a", "read": False}, {"id": "b", "read": False}])
    result = collector.mark_read()
    assert result["marked"] == 2
    assert all(item["read"] for item in json.loads(path.read_text()))
