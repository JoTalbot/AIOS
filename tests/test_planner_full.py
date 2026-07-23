"""Planner full tests."""
from aios_core.planner import Planner
def test_planner_ops():
    p = Planner()
    assert p.stats() is not None
