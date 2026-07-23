"""Parametrized: AB full matrix."""
import pytest
from aios_core.ab_testing import ABTest

@pytest.mark.parametrize("w_a,w_b", [(0.5,0.5),(0.6,0.4),(0.7,0.3),(0.8,0.2),(0.9,0.1)])
def test_weighted_ratio(w_a, w_b):
    ab = ABTest("t", {"a": w_a, "b": w_b})
    ca = cb = 0
    for i in range(3000):
        if ab.assign_variant(f"u{i}") == "a": ca += 1
        else: cb += 1
    actual = ca / (ca + cb)
    assert abs(actual - w_a) < 0.08

@pytest.mark.parametrize("names", [["x","y"],["a","b","c"],["v1","v2","v3","v4","v5"]])
def test_variant_set(names):
    weights = {n: 1.0/len(names) for n in names}
    ab = ABTest("t", weights)
    seen = set()
    for _ in range(500): seen.add(ab.assign_variant("u"))
    assert seen == set(names)
