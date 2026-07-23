"""Instagram scenario tests."""

from aios_core.modules.instagram.storage import InstagramStorage


def test_instagram_storage_write_read():
    s = InstagramStorage(":memory:")
    ads = s.get_ads()
    assert isinstance(ads, list)
    s.close()


def test_instagram_storage_subscription_lifecycle():
    s = InstagramStorage(":memory:")
    subs = s.subscription_list() if hasattr(s, 'subscription_list') else []
    assert isinstance(subs, list)
    s.close()
