"""test_ab_testing_scenario test."""
from aios_core.ab_testing import ABTest

def test_weighted_distribution():
    ab = ABTest("test", {"a": 0.9, "b": 0.1})
    counts = {"a": 0, "b": 0}
    for i in range(500):
        v = ab.assign_variant(f"u{i}")
        counts[v] += 1
    assert counts["a"] > counts["b"]
