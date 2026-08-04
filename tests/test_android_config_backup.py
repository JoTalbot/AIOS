"""Token-free Android configuration backup test."""
from __future__ import annotations

import json


def test_config_backup_excludes_endpoint_and_tokens(monkeypatch, tmp_path):
    import run_android_config_backup as backup

    monkeypatch.setattr(backup, "ROOT", tmp_path)
    monkeypatch.setattr(backup, "BACKUPS", tmp_path / "backups" / "android_config")

    class Inventory:
        def __init__(self, root): pass
        def record(self): return {"android": "15", "sdk": 35, "companion_version": "0.1", "wireguard_active": True, "apps_available": 6, "apps_calibrated": 3, "calibrations_stale": 0, "availability_drift": [], "version_drift": [], "token": "must_not_export"}

    class Center:
        def __init__(self, root): pass
        def snapshot(self): return {"leads": {}, "bank_tasks": {}, "templates": {}, "timers": {}, "state_health": {}, "recovery": {}, "serial": "must_not_export"}

    monkeypatch.setattr(backup, "PhoneInventory", Inventory)
    monkeypatch.setattr(backup, "PhoneControlCenter", Center)
    assert backup.main() == 0
    file = next(backup.BACKUPS.glob("*.json"))
    raw = file.read_text()
    assert "must_not_export" not in raw
    assert file.stat().st_mode & 0o777 == 0o600
