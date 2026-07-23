"""quantum_nlp test."""
def test(): from aios_core.quantum_nlp import QuantumNLP; s = QuantumNLP().stats(); assert isinstance(s, dict)
