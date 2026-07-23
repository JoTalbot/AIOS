"""Tests for remaining quantum and neuromorphic modules."""

from aios_core.quantum_optimization import QuantumOptimizer
from aios_core.quantum_native import QuantumNativeRuntime
from aios_core.neuromorphic_matrix import NeuromorphicMatrix


def test_quantum_optimizer_stats():
    qo = QuantumOptimizer()
    s = qo.stats()
    assert isinstance(s, dict)


def test_quantum_native_stats():
    qn = QuantumNativeRuntime()
    s = qn.stats()
    assert isinstance(s, dict)


def test_neuromorphic_matrix_stats():
    nm = NeuromorphicMatrix()
    s = nm.stats()
    assert isinstance(s, dict)
