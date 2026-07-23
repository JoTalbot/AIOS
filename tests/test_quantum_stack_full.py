"""test_quantum_stack_full test."""
from aios_core.quantum_computing import QuantumCircuit
from aios_core.quantum_ml import QuantumML
from aios_core.quantum_cryptography import QuantumCryptography
from aios_core.quantum_internet import QuantumInternet
from aios_core.quantum_native import QuantumNativeRuntime
from aios_core.quantum_optimization import QuantumOptimizer

def test_all_quantum():
    for cls in [QuantumCircuit(2), QuantumML(), QuantumCryptography(), QuantumInternet(), QuantumNativeRuntime(), QuantumOptimizer()]:
        s = cls.stats()
        assert isinstance(s, dict)

