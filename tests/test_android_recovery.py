"""Tests for safe Android recovery diagnosis without device content."""
from __future__ import annotations


class Gateway:
    def __init__(self, root, connected=True, companion=True):
        self.root = root
        self._connected = connected
        self._companion = companion

    @property
    def serial(self):
        return "paired" if self._connected or self._companion else "paired"

    def connect(self):
        return {"status": "ok" if self._connected else "error"}

    def status(self):
        return {"connected": self._connected, "companion": {"connected": self._companion}}


def test_recovery_reports_endpoint_action_when_companion_still_online(tmp_path):
    from aios_core.android_recovery import AndroidRecovery

    report = AndroidRecovery(tmp_path, gateway_factory=lambda root: Gateway(root, connected=False, companion=True)).check()
    assert report["action"] == "wireless_debug_endpoint_needed"
    assert report["adb_connected"] is False
    assert report["companion_connected"] is True
    assert (tmp_path / "data" / "android_gateway" / "recovery.json").stat().st_mode & 0o777 == 0o600


def test_recovery_ok_when_adb_and_companion_work(tmp_path):
    from aios_core.android_recovery import AndroidRecovery

    report = AndroidRecovery(tmp_path, gateway_factory=lambda root: Gateway(root, connected=True, companion=True)).check()
    assert report["status"] == "ok"
    assert report["action"] == "none"
