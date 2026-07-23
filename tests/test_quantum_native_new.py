"""quantum_native test."""
def test(): from aios_core.quantum_native import QuantumNativeRuntime; s = QuantumNativeRuntime().stats(); assert isinstance(s, dict)
