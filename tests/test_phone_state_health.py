"""Tests for metadata-only Android state integrity health."""
from __future__ import annotations

import json


def test_state_health_detects_invalid_json_and_reports_vpn(tmp_path):
    from aios_core.phone_state_health import PhoneStateHealth

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "notifications.json").write_text("{broken", encoding="utf-8")
    report = PhoneStateHealth(tmp_path, service_probe=lambda name: name == "wg-quick@wg0.service").snapshot()
    assert report["status"] == "degraded"
    assert "notifications.json" in report["invalid"]
    assert report["wireguard_active"] is True
