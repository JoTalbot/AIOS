"""Test AI safety benchmark."""
from aios_core.ai_safety_benchmark import SafetyBenchmark
def test_benchmark(): assert SafetyBenchmark().stats() is not None
