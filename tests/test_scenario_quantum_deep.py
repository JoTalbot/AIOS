"""Quantum deep scenario."""
from aios_core.quantum_computing import QuantumCircuit
from aios_core.quantum_native import QuantumNativeRuntime
from aios_core.quantum_ml import QuantumML
from aios_core.quantum_optimization import QuantumOptimizer
from aios_core.quantum_cryptography import QuantumCryptography
from aios_core.quantum_internet import QuantumInternet

def test_quantum_deep():
    assert QuantumCircuit(4).stats() is not None
    assert QuantumNativeRuntime().stats() is not None
    assert QuantumML().stats() is not None
    assert QuantumOptimizer().stats() is not None
    assert QuantumCryptography().stats() is not None
    assert QuantumInternet().stats() is not None
