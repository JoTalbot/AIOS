"""quantum_advantage test."""
def test(): from aios_core.quantum_advantage import QuantumAdvantage; s = QuantumAdvantage().stats(); assert isinstance(s, dict)
