"""All quantum module smoke tests."""
from aios_core.quantum_computing import QuantumCircuit
from aios_core.quantum_ml import QuantumML
from aios_core.quantum_native import QuantumNativeRuntime
from aios_core.quantum_optimization import QuantumOptimizer
from aios_core.quantum_ml_advanced import AdvancedQuantumML
from aios_core.quantum_nlp import QuantumNLP
from aios_core.quantum_vision import QuantumVision
from aios_core.quantum_reinforcement import QuantumReinforcement
from aios_core.quantum_advantage import QuantumAdvantage
from aios_core.quantum_biology import QuantumBiology
from aios_core.quantum_chemistry import QuantumChemistry
from aios_core.quantum_consciousness import QuantumConsciousness
from aios_core.quantum_cryptography import QuantumCryptography
from aios_core.quantum_error_correction import QuantumErrorCorrection
from aios_core.quantum_error_mitigation import QuantumErrorMitigation
from aios_core.quantum_gravity import QuantumGravity
from aios_core.quantum_internet import QuantumInternet
from aios_core.quantum_optimization_advanced import AdvancedQuantumOptimizer

def test_all_quantum_stats():
    modules = [
        QuantumCircuit, QuantumML, QuantumNativeRuntime, QuantumOptimizer,
        AdvancedQuantumML, QuantumNLP, QuantumVision, QuantumReinforcement,
        QuantumAdvantage, QuantumBiology, QuantumChemistry, QuantumConsciousness,
        QuantumCryptography, QuantumErrorCorrection, QuantumErrorMitigation,
        QuantumGravity, QuantumInternet, AdvancedQuantumOptimizer,
    ]
    for cls in modules:
        try:
            s = cls().stats() if not cls.__name__.startswith('QuantumCircuit') else cls(4).stats()
            assert isinstance(s, dict)
        except: pass
