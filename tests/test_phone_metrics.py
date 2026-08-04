"""Metadata-only metrics history and export tests."""
from __future__ import annotations


def _snapshot(leads=1):
    return {
        "device": {"connected": True, "companion": True, "location_ready": True, "camera_permission": True, "microphone_permission": False},
        "apps": [{"available": True, "calibrated": True}],
        "leads": {"pending": leads, "by_source": {"WhatsApp": leads}, "crm_open": 0, "crm_attention": 0, "crm_overdue": 0},
        "banks": [{"title": "A-Bank", "unread_notifications": 0}],
        "bank_tasks": {"pending": 0, "attention": 0, "overdue": 0},
        "templates": {"count": 0, "stale": 0, "used_total": 0},
        "audit": {"count": 1},
        "timers": {"a": True},
    }


def test_metrics_store_history_trend_and_private_csv(tmp_path):
    from aios_core.phone_metrics import PhoneMetricsStore

    store = PhoneMetricsStore(tmp_path)
    store.record(_snapshot(1))
    store.record(_snapshot(3))
    trend = store.trend(7)
    assert trend["snapshots"] == 2
    assert trend["changes"]["leads_pending"] == 2
    availability = store.availability(7)
    assert availability["adb_pct"] == 100
    target = store.export_csv()
    assert target.exists()
    assert target.stat().st_mode & 0o777 == 0o600
    content = target.read_text()
    assert "leads_pending" in content
    assert "message" not in content.casefold()
