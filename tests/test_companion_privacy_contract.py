"""Static contract tests for the Companion privacy/network boundary."""
from __future__ import annotations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_companion_ui_defaults_to_controls_and_reports_package():
    source = (ROOT / "android_companion/app/src/main/java/ua/aios/companion/AIOSAccessibilityService.java").read_text()
    assert "return snapshot(false);" in source
    assert '.put("package", packageName)' in source
    assert "if (includeText)" in source


def test_companion_binds_only_to_wireguard_address():
    source = (ROOT / "android_companion/app/src/main/java/ua/aios/companion/CompanionService.java").read_text()
    assert "wireGuardAddress()" in source
    assert 'candidate.bind(new InetSocketAddress(tunnel, PORT));' in source
    assert 'address.getHostAddress().startsWith("10.203.")' in source
    assert 'AIOSAccessibilityService.snapshot("full".equalsIgnoreCase' in source
