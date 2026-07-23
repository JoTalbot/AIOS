"""Full tests for OLX own ads tracker."""

from aios_core.modules.olx.own_ads import OwnAdsTracker


def test_tracker_init_with_none_storage():
    t = OwnAdsTracker(None)
    assert t is not None
