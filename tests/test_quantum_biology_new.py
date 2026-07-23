"""quantum_biology test."""
def test(): from aios_core.quantum_biology import QuantumBiology; s = QuantumBiology().stats(); assert isinstance(s, dict)
