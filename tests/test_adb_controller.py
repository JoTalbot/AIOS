"""Tests for ADB controller."""
from aios_core.modules.olx.adb import ADBController
def test_adb_controller_init():
    a = ADBController()
    assert a is not None
