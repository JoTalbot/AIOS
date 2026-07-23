"""quantum_cryptography test."""
def test(): from aios_core.quantum_cryptography import QuantumCryptography; s = QuantumCryptography().stats(); assert isinstance(s, dict)
