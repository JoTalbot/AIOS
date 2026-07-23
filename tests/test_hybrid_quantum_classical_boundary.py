"""hybrid_quantum_classical boundary test."""
from aios_core.hybrid_quantum_classical import HybridQuantumClassical

def test_no_backend(): r = HybridQuantumClassical().execute_hybrid(lambda d:d, lambda d:d, {"x":1}); assert r["fallback"] is True
