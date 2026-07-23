"""Tests for OLX subscription manager."""

from aios_core.modules.olx.subscriptions import SubscriptionManager


def test_subscription_manager_init():
    sm = SubscriptionManager()
    assert sm is not None
