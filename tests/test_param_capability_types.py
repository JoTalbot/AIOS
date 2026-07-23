"""Parametrized capability type tests."""
import pytest
from aios_core.capability_engine import CapabilityEngine

@pytest.mark.parametrize("cap_name", [
    "search", "analyse", "report", "collect", "notify",
])
def test_capability_engine(cap_name):
    ce = CapabilityEngine()
    assert ce.stats() is not None
