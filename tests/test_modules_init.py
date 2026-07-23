"""Tests for module initialization across platforms."""

from aios_core.modules.instagram import InstagramStorage
from aios_core.modules.facebook import FacebookStorage
from aios_core.modules.whatsapp import WhatsAppStorage
from aios_core.modules.viber import ViberStorage
from aios_core.modules.tiktok import TikTokStorage


def test_instagram_storage_init():
    s = InstagramStorage(":memory:")
    assert s is not None
    s.close()


def test_facebook_storage_init():
    s = FacebookStorage(":memory:")
    assert s is not None
    s.close()


def test_whatsapp_storage_init():
    s = WhatsAppStorage(":memory:")
    assert s is not None
    s.close()


def test_viber_storage_init():
    s = ViberStorage(":memory:")
    assert s is not None
    s.close()


def test_tiktok_storage_init():
    s = TikTokStorage(":memory:")
    assert s is not None
    s.close()
