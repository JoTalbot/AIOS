"""Parametrized planner goal types."""
import pytest
from aios_core.planner import Planner

@pytest.mark.parametrize("goal_count", [1, 3, 5, 10])
def test_planner_stats(goal_count):
    p = Planner()
    for _ in range(goal_count):
        pass
    assert p.stats() is not None
