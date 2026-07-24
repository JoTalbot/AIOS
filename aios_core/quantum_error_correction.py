"""Quantum Error Correction for AIOS"""

from typing import List


class QuantumErrorCorrection:
    """Basic quantum error correction codes."""

    def __init__(self):
        """Initialize QuantumErrorCorrection."""
        self.codes = {"repetition": 3, "surface": 9}

    def encode(self, logical_qubit: int, code: str = "repetition") -> list[int]:
        """Execute encode."""
        if code == "repetition":
            return [logical_qubit] * self.codes["repetition"]
        return [logical_qubit] * 3

    def decode(self, physical_qubits: list[int]) -> int:
        """Execute decode."""
        # Majority vote
        return 1 if sum(physical_qubits) > len(physical_qubits) // 2 else 0

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"codes": list(self.codes.keys())}
