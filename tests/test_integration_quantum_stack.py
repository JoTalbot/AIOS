"""Integration: Quantum stack."""
from aios_core.quantum_computing import QuantumCircuit
from aios_core.quantum_native import QuantumNativeRuntime
from aios_core.quantum_ml import QuantumML
from aios_core.quantum_cryptography import QuantumCryptography

def test_quantum_stack():
    qc = QuantumCircuit(2)
    qn = QuantumNativeRuntime()
    qml = QuantumML()
    qcrypto = QuantumCryptography()
    assert qc.stats() is not None
    assert qn.stats() is not None
    assert qml.stats() is not None
    assert qcrypto.stats() is not None
