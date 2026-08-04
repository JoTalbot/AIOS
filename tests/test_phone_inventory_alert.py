"""Inventory alert only reports aggregate drift counts."""
from __future__ import annotations


def test_inventory_alert_dry_baseline_and_drift(monkeypatch, tmp_path):
    import run_phone_inventory_alert as alert

    monkeypatch.setattr(alert, "ROOT", tmp_path)
    monkeypatch.setattr(alert, "STATE", tmp_path / "state.json")

    class Inventory:
        def __init__(self, root): pass
        def record(self): return {"availability_drift": ["x"], "version_drift": [], "calibrations_stale": 0}

    sent = []
    monkeypatch.setattr(alert, "_send", lambda text: sent.append(text) or True)
    baseline = alert.check(bootstrap=True, inventory_factory=Inventory)
    assert baseline["sent"] is False
    report = alert.check(alert=True, inventory_factory=Inventory)
    assert report["sent"] is True
    assert "x" not in sent[0]
