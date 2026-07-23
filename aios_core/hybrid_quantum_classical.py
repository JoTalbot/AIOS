"""Hybrid Quantum-Classical Computing for AIOS"""

from typing import Any, Callable, Dict


class HybridQuantumClassical:
    """Interface between quantum and classical computation."""

    def __init__(self):
        self.quantum_backend = None
        self.classical_fallback = True

    def set_quantum_backend(self, backend: Any):
        self.quantum_backend = backend

    def execute_hybrid(self, quantum_part: Callable, classical_part: Callable, data: Any) -> Dict:
        try:
            if self.quantum_backend:
                q_result = quantum_part(data)
                c_result = classical_part(q_result)
                return {"quantum": q_result, "classical": c_result, "hybrid": True}
        except:
            pass
        return {"result": classical_part(data), "hybrid": False, "fallback": True}

    def stats(self) -> dict:
        return {"quantum_available": self.quantum_backend is not None}
