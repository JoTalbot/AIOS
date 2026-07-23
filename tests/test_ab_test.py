"""Tests for AB testing variant assignment."""

from aios_core.ab_testing import ABTest


def test_single_variant_full_weight():
    ab = ABTest("test", {"control": 1.0})
    assert ab.assign_variant("user1") == "control"
    assert ab.assign_variant("user2") == "control"


def test_stats_clean():
    ab = ABTest("pricing", {"a": 0.5, "b": 0.5})
    s = ab.stats()
    assert s["name"] == "pricing"
    assert s["results"]["a"] == 0
