"""Complete Facebook module tests."""

from aios_core.modules.facebook.storage import FacebookStorage
from aios_core.platforms import get_platform


def test_facebook_storage_init():
    s = FacebookStorage(":memory:")
    assert s is not None
    s.close()


def test_facebook_platform_registered():
    desc = get_platform("facebook")
    assert desc.android_package == "com.facebook.katana"
