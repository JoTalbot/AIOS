"""Integration test — orchestration pipeline."""
from aios_core.orchestrator import Orchestrator
from aios_core.planner import Planner
from aios_core.capability_engine import CapabilityEngine
def test_pipeline_triple():
    assert Orchestrator() is not None
    assert Planner() is not None
    assert CapabilityEngine() is not None
