"""Parametrized A/B testing."""
import pytest
from aios_core.ab_testing import ABTest

@pytest.mark.parametrize("weights,expected_keys", [
    ({"a": 0.5, "b": 0.5}, {"a", "b"}),
    ({"control": 0.8, "test": 0.2}, {"control", "test"}),
    ({"x": 0.3, "y": 0.3, "z": 0.4}, {"x", "y", "z"}),
    ({"only": 1.0}, {"only"}),
])
def test_ab_variant_keys(weights, expected_keys):
    ab = ABTest("test", weights)
    for _ in range(50):
        assert ab.assign_variant("u") in expected_keys
