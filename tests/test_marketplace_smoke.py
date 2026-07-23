"""Smoke tests for marketplace and promotion modules."""

from aios_core.marketplace import Marketplace


def test_marketplace_stats():
    m = Marketplace()
    s = m.stats()
    assert isinstance(s, dict)


def test_marketplace_search_empty():
    m = Marketplace()
    results = m.search("test")
    assert isinstance(results, list)
