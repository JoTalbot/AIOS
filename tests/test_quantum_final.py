"""Tests for quantum error mitigation, optimization advanced, and gravity."""

from aios_core.quantum_error_mitigation import QuantumErrorMitigation
from aios_core.quantum_optimization_advanced import AdvancedQuantumOptimizer
from aios_core.quantum_gravity import QuantumGravity


def test_quantum_error_mitigation_stats():
    s = QuantumErrorMitigation().stats()
    assert isinstance(s, dict)


def test_advanced_quantum_optimizer_stats():
    s = AdvancedQuantumOptimizer().stats()
    assert isinstance(s, dict)


def test_quantum_gravity_stats():
    s = QuantumGravity().stats()
    assert isinstance(s, dict)
