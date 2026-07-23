import pytest
from aios_core.ab_testing import ABTest

@pytest.mark.parametrize("weights", [
    {"a":0.5,"b":0.5}, {"a":0.7,"b":0.3}, {"a":0.9,"b":0.1},
    {"x":0.33,"y":0.33,"z":0.34}, {"ctrl":1.0},
])
def test_all_variants_returned(weights):
    ab = ABTest("t", weights)
    seen = set()
    for _ in range(200):
        seen.add(ab.assign_variant("u"))
    keys = set(weights.keys())
    assert seen == keys
