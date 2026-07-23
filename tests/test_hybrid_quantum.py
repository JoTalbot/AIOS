"""Tests for hybrid quantum-classical computing."""

from aios_core.hybrid_quantum_classical import HybridQuantumClassical


def test_classical_fallback():
    hq = HybridQuantumClassical()
    result = hq.execute_hybrid(lambda d: d, lambda d: {"out": d}, {"input": 1})
    assert result["hybrid"] is False
    assert result["fallback"] is True
    assert result["result"]["out"]["input"] == 1
