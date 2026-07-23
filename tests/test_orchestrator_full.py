"""Orchestrator full tests."""
from aios_core.orchestrator import Orchestrator
def test_orchestrator_ops():
    o = Orchestrator()
    assert o.stats() is not None
