"""quantum_chemistry test."""
def test(): from aios_core.quantum_chemistry import QuantumChemistry; s = QuantumChemistry().stats(); assert isinstance(s, dict)
