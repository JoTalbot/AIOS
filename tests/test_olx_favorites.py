"""Tests for OLX favorites watch."""

from aios_core.modules.olx.favorites import FavoritesWatch


def test_favorites_watch_init():
    fw = FavoritesWatch()
    assert fw is not None
