"""Hybrid Quantum-Classical Computing for AIOS"""

import logging
from typing import Any, Callable, Dict

__all__ = ["HybridQuantumClassical"]

logger = logging.getLogger(__name__)


class HybridQuantumClassical:
    """Interface between quantum and classical computation."""

    def __init__(self):
        """Initialize HybridQuantumClassical."""
        self.quantum_backend = None
        self.classical_fallback = True

    def set_quantum_backend(self, backend: Any) -> None:
        """Execute set quantum backend."""
        self.quantum_backend = backend

    def execute_hybrid(self, quantum_part: Callable, classical_part: Callable, data: Any) -> Dict:
        """Execute execute hybrid."""
        try:
            if self.quantum_backend:
                q_result = quantum_part(data)
                c_result = classical_part(q_result)
                return {"quantum": q_result, "classical": c_result, "hybrid": True}
        except Exception as exc:
            logger.warning("Hybrid execution failed, falling back to classical: %s", exc)
        return {"result": classical_part(data), "hybrid": False, "fallback": True}

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"quantum_available": self.quantum_backend is not None}
