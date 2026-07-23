"""Parametrized AB testing convergence."""
import pytest
from aios_core.ab_testing import ABTest

@pytest.mark.parametrize("weight_a", [0.5, 0.6, 0.7, 0.8, 0.9])
def test_weighted_convergence(weight_a):
    weight_b = 1.0 - weight_a
    ab = ABTest("conv", {"a": weight_a, "b": weight_b})
    counts = {"a": 0, "b": 0}
    for i in range(2000):
        v = ab.assign_variant(f"u{i}")
        counts[v] += 1
    actual_ratio_a = counts["a"] / 2000
    assert abs(actual_ratio_a - weight_a) < 0.1

@pytest.mark.parametrize("n_variants", [2, 3, 5, 10])
def test_n_variants_distribution(n_variants):
    variants = {f"v{i}": 1.0/n_variants for i in range(n_variants)}
    ab = ABTest("multi", variants)
    seen = set()
    for _ in range(500):
        seen.add(ab.assign_variant("u"))
    assert len(seen) == n_variants
