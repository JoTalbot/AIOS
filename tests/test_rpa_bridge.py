"""Tests for Android RPA bridge and APK converter."""

from aios_core.android_rpa_bridge import AndroidRPAManager


def test_rpa_manager_init():
    rm = AndroidRPAManager()
    assert rm is not None
