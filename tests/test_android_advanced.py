"""Batch tests for Android modules (execution, fleet, observability, appium)."""

from aios_core.android_execution import RealDeviceExecutor
from aios_core.android_fleet import DevicePool
from aios_core.android_observability import AndroidObservability


def test_executor_stats():
    e = RealDeviceExecutor("emulator-5554")
    s = e.stats()
    assert isinstance(s, dict)


def test_device_pool_stats():
    dp = DevicePool()
    s = dp.stats()
    assert isinstance(s, dict)


def test_android_observability_stats():
    ao = AndroidObservability("emulator-5554")
    s = ao.stats()
    assert isinstance(s, dict)
