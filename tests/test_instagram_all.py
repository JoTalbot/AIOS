"""Tests for Instagram module components."""

from aios_core.modules.instagram import InstagramStorage, InstagramCollector
from aios_core.modules.instagram.login import InstagramLoginDriver
from aios_core.modules.instagram.own_posts import OwnPostsParser


def test_storage_create():
    s = InstagramStorage(":memory:")
    assert s is not None
    s.close()


def test_collector_init():
    c = InstagramCollector()
    assert c is not None


def test_login_driver():
    d = InstagramLoginDriver()
    assert d is not None


def test_own_posts_parser():
    p = OwnPostsParser()
    assert p is not None
