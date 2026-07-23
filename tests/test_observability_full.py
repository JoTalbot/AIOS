"""Observability stack full."""
from aios_core.observability import ObservabilityStack
def test(): s=ObservabilityStack().stats(); assert isinstance(s,dict)
