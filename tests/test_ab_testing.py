"""Tests for A/B Testing Framework."""

from aios_core.ab_testing import ABTest


def test_ab_assigns_variant():
    ab = ABTest("button_color", {"blue": 0.5, "red": 0.5})
    variant = ab.assign_variant("user123")
    assert variant in ("blue", "red")


def test_ab_deterministic_for_full_weight():
    ab = ABTest("layout", {"a": 1.0})
    assert ab.assign_variant("any") == "a"


def test_ab_records_and_picks_winner():
    ab = ABTest("pricing", {"low": 0.5, "high": 0.5})
    ab.record_result("low", True)
    ab.record_result("low", True)
    ab.record_result("high", True)
    assert ab.get_winner() == "low"


def test_ab_stats():
    ab = ABTest("notification", {"on": 0.7, "off": 0.3})
    ab.record_result("on", True)
    s = ab.stats()
    assert s["name"] == "notification"
    assert s["results"]["on"] == 1
    assert s["results"]["off"] == 0


def test_ab_record_failure_does_not_count():
    ab = ABTest("test", {"a": 1.0})
    ab.record_result("a", False)
    assert ab.stats()["results"]["a"] == 0
