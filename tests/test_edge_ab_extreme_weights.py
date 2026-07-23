"""Edge: AB testing with extreme weights."""
from aios_core.ab_testing import ABTest

def test_single_variant():
    ab = ABTest("t", {"only": 1.0})
    for _ in range(1000):
        assert ab.assign_variant("u") == "only"

def test_many_variants():
    variants = {f"v{i}": 1.0/i for i in range(1, 51)}
    total = sum(variants.values())
    variants = {k: v/total for k, v in variants.items()}
    ab = ABTest("many", variants)
    seen = set()
    for _ in range(1000):
        seen.add(ab.assign_variant("u"))
    assert len(seen) > 1
