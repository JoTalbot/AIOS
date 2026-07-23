"""Mamba / State Space Models for AIOS"""

from typing import List


class MambaBlock:
    """Simplified Mamba (Selective State Space Model)."""

    def __init__(self, d_model: int = 512, d_state: int = 16):
        self.d_model = d_model
        self.d_state = d_state
        self.state = [0.0] * d_state

    def forward(self, x: list[float]) -> list[float]:
        """Execute forward."""
        # Simplified selective SSM
        output = []
        for val in x:
            self.state = [s * 0.9 + val * 0.1 for s in self.state]
            output.append(sum(self.state) / len(self.state))
        return output

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"d_model": self.d_model, "d_state": self.d_state}
