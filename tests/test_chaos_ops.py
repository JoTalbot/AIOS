"""Chaos monkey operations tests."""
from aios_core.chaos import ChaosMonkey
from aios_core.chaos_testing import ChaosTester
def test_chaos_ops():
    assert ChaosMonkey().stats() is not None
    assert ChaosTester().stats() is not None
