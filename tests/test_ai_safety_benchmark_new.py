"""AI safety benchmark new."""
from aios_core.ai_safety_benchmark import SafetyBenchmark
def test(): s=SafetyBenchmark().stats(); assert isinstance(s,dict)
