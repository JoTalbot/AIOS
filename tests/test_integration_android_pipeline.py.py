"""Integration: Android modules pipeline."""
from aios_core.android_driver import DriverCapabilities
from aios_core.android_registry import AndroidAppRegistry
def test_android_pipeline():
    dc = DriverCapabilities(package="com.test")
    ar = AndroidAppRegistry()
    assert dc.package == "com.test"
    assert ar.stats() is not None
