"""Tests for orchestrator and planner modules."""

from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner


def test_orchestrator_init():
    o = Orchestrator()
    assert o is not None


def test_orchestrator_stats():
    o = Orchestrator()
    s = o.stats()
    assert isinstance(s, dict)


def test_planner_init():
    p = Planner()
    assert p is not None
