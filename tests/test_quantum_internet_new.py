"""quantum_internet test."""
def test(): from aios_core.quantum_internet import QuantumInternet; s = QuantumInternet().stats(); assert isinstance(s, dict)
