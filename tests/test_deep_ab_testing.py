"""Deep AB testing — statistical properties."""
from aios_core.ab_testing import ABTest
def test_large_sample_convergence():
    ab = ABTest("conv", {"a": 0.7, "b": 0.3})
    counts = {"a": 0, "b": 0}
    for i in range(10000):
        v = ab.assign_variant(f"u{i}")
        counts[v] += 1
    ratio = counts["a"] / counts["b"]
    assert 1.5 < ratio < 5.0
def test_record_wins():
    ab = ABTest("w", {"x": 0.5, "y": 0.5})
    ab.record_result("x", True); ab.record_result("x", True); ab.record_result("y", True)
    assert ab.get_winner() == "x"
