"""Orchestrator full ops."""
from aios_core.orchestrator import Orchestrator
def test_stats(): assert Orchestrator().stats() is not None
