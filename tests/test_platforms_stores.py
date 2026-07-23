"""Tests for platform resolvers, stores, and profile management."""

from aios_core.platforms.resolver import resolve_profile
from aios_core.platforms.store import ProfileStore


def test_profile_store_init():
    ps = ProfileStore(":memory:")
    assert ps is not None


def test_profile_store_list_empty():
    ps = ProfileStore(":memory:")
    profiles = ps.list("olx")
    assert isinstance(profiles, list)
