"""Integration: Constitution + Ethics cross-module."""
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.ai_ethics import AIEthicsFramework
def test_constitution_ethics_pipeline():
    ce = ConstitutionEngine()
    ef = AIEthicsFramework()
    assert ce.stats() is not None
    r = ef.evaluate_action({"action": "test_action"})
    assert isinstance(r, dict)
