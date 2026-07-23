"""OLX subscription operations tests."""
from aios_core.modules.olx.subscriptions import SubscriptionManager
from aios_core.modules.olx.favorites import FavoritesWatch
def test_subscription_tools():
    assert SubscriptionManager is not None
    assert FavoritesWatch is not None
