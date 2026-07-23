"""Integration: Planner + Orchestrator pipeline."""
from aios_core.planner import Planner
from aios_core.orchestrator import Orchestrator
def test_planner_orchestrator_pipeline():
    p = Planner()
    o = Orchestrator()
    assert p.stats() is not None
    assert o.stats() is not None
