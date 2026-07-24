"""Orchestration — planner, orchestrator, capabilities."""
from aios_core.capability_engine import CapabilityEngine
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner


def test_orch_flow():
    p = Planner()
    o = Orchestrator()
    ce = CapabilityEngine()
    assert p.stats() is not None
    assert o.stats() is not None
    assert ce.stats() is not None
