"""Complete TikTok module tests."""

from aios_core.modules.tiktok.storage import TikTokStorage
from aios_core.platforms import get_platform


def test_tiktok_storage_init():
    s = TikTokStorage(":memory:")
    assert s is not None
    s.close()


def test_tiktok_platform_registered():
    desc = get_platform("tiktok")
    assert desc.android_package == "com.zhiliaoapp.musically"
