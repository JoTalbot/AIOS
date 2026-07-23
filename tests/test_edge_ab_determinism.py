"""Edge: AB determinism."""
from aios_core.ab_testing import ABTest
def test_deterministic_full_weight():
    ab = ABTest("t", {"only": 1.0})
    for _ in range(100): assert ab.assign_variant("u") == "only"
