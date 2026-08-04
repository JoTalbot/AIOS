"""Tests for the metadata-only consolidated phone control center."""
from __future__ import annotations


class Gateway:
    def __init__(self, root):
        self.root = root

    def status(self):
        return {
            "connected": True,
            "model": "G1",
            "android": "15",
            "companion": {"connected": True},
        }

    def capture_status(self):
        return {"status": "ok", "camera_permission": True, "microphone_permission": False, "background_capture": False}

    def location_status(self):
        return {"status": "ok", "permission": True, "ready": False}

    def app_profiles(self):
        return {"profiles": [
            {"id": "whatsapp", "title": "WhatsApp", "available": True},
            {"id": "easyway", "title": "EasyWay", "available": True},
        ]}


def test_control_center_has_no_screen_or_message_payload(tmp_path):
    from aios_core.phone_control_center import PhoneControlCenter, format_telegram

    class Banks:
        def __init__(self, root): pass
        def snapshot(self): return {"banks": [{"title": "A-Bank", "available": True, "unread_notifications": 0}]}

    class StateHealth:
        def __init__(self, root): pass
        def snapshot(self): return {"status": "ok", "invalid": [], "total_bytes": 0, "backup_age_hours": 1.0, "wireguard_active": True}

    class Sync:
        def __init__(self, root): pass
        def snapshot(self): return {"fresh": 2, "total": 2, "sources": []}

    class Inventory:
        def __init__(self, root): pass
        def latest(self): return {"android": "15", "sdk": 35, "apps_available": 2, "apps_calibrated": 1, "calibrations_stale": 0, "availability_drift": []}

    class Jobs:
        def __init__(self, root): pass
        def snapshot(self, record=False): return {"status": "ok", "active": 2, "total": 2, "backup": {"retention_ok": True}}

    report = PhoneControlCenter(tmp_path, gateway_factory=Gateway, service_probe=lambda _name: True, bank_monitor_factory=Banks, state_health_factory=StateHealth, sync_status_factory=Sync, inventory_factory=Inventory, jobs_factory=Jobs).snapshot()
    assert report["status"] == "ok"
    assert report["device"]["connected"] is True
    assert report["leads"]["pending"] == 0
    text = format_telegram(report)
    assert "ЦЕНТР УПРАВЛЕНИЯ" in text
    assert "сообщени" not in text.casefold()
