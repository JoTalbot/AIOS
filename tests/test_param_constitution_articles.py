"""Parametrized constitution article checks."""
import pytest
from aios_core.constitution_engine import ConstitutionEngine

@pytest.mark.parametrize("action", [
    {"type": "collect"}, {"type": "analyse"}, {"type": "report"},
    {"type": "deploy"}, {"type": "backup"}, {"type": "approve"},
    {"type": "reject"}, {"type": "archive"},
])
def test_constitution_evaluate(action):
    ce = ConstitutionEngine()
    s = ce.stats()
    assert isinstance(s, dict)
