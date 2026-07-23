"""Tests for quantum computing modules."""

from aios_core.quantum_computing import QuantumCircuit
from aios_core.quantum_ml import QuantumML


def test_quantum_circuit_stats():
    qc = QuantumCircuit(4)
    s = qc.stats()
    assert isinstance(s, dict)


def test_quantum_ml_stats():
    qml = QuantumML()
    s = qml.stats()
    assert isinstance(s, dict)
