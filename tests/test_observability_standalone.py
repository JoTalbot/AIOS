"""Observability standalone test."""
from aios_core.observability import ObservabilityStack
def test_init(): assert ObservabilityStack() is not None
