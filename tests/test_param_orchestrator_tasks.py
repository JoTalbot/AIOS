"""Parametrized orchestrator task types."""
import pytest
from aios_core.orchestrator import Orchestrator

@pytest.mark.parametrize("task_types", [1, 5, 10])
def test_orchestrator_stats(task_types):
    o = Orchestrator()
    assert o.stats() is not None
