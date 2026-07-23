"""Parametrized A/B testing tests."""

import pytest
from aios_core.ab_testing import ABTest


@pytest.mark.parametrize("weights", [
    {"a": 0.5, "b": 0.5},
    {"control": 0.7, "variant": 0.3},
    {"x": 1.0},
])
def test_assign_returns_valid_variant(weights):
    ab = ABTest("test", weights)
    variant = ab.assign_variant("user1")
    assert variant in weights


@pytest.mark.parametrize("variant,success,expected", [
    ("a", True, 1), ("a", False, 0), ("b", True, 1),
])
def test_record_result_counts(variant, success, expected):
    ab = ABTest("test", {"a": 0.5, "b": 0.5})
    ab.record_result(variant, success)
    assert ab.stats()["results"][variant] == expected
