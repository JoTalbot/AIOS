"""Kolmogorov-Arnold Networks (KAN) for AIOS v10.9.0.

KAN with B-spline activation functions, layer
management, network composition, training
simulation, and symbolic regression.

Classes:
    KANLayer       — KAN layer with spline activations
    KAN            — full Kolmogorov-Arnold Network
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KANLayer:
    """KAN layer with B-spline-like activations."""

    in_dim: int = 2
    out_dim: int = 2
    grid_size: int = 5
    coefficients: list[list[float]] = field(default_factory=list)
    _trained: bool = False

    def __post_init__(self) -> None:
        if not self.coefficients:
            self.coefficients = [
                [random.gauss(0, 0.1) for _ in range(self.grid_size)]
                for _ in range(self.in_dim * self.out_dim)
            ]

    def _spline_activation(self, x: float, coeffs: list[float]) -> float:
        """Compute B-spline-like activation from coefficients."""
        # Piecewise linear interpolation using coefficients as values
        t = (x + 1) / 2  # map [-1,1] to [0,1]
        t = max(0, min(1, t))
        idx = int(t * (len(coeffs) - 1))
        if idx >= len(coeffs) - 1:
            return coeffs[-1]
        frac = t * (len(coeffs) - 1) - idx
        return coeffs[idx] * (1 - frac) + coeffs[idx + 1] * frac

    def forward(self, x: list[float]) -> list[float]:
        """Forward pass through KAN layer (backward-compatible)."""
        if not x:
            return [0.0] * self.out_dim

        output = [0.0] * self.out_dim
        for out_idx in range(self.out_dim):
            val = 0.0
            for in_idx in range(min(self.in_dim, len(x))):
                coeff_idx = in_idx * self.out_dim + out_idx
                if coeff_idx < len(self.coefficients):
                    val += self._spline_activation(
                        x[in_idx], self.coefficients[coeff_idx]
                    )
                else:
                    val += x[in_idx] * 0.1
            output[out_idx] = val
        return output

    def update_coefficients(self, gradients: list[float], lr: float = 0.01) -> None:
        """Update coefficients from gradients."""
        for i in range(min(len(self.coefficients), len(gradients))):
            for j in range(len(self.coefficients[i])):
                self.coefficients[i][j] -= lr * gradients[i % len(gradients)]

    def stats(self) -> dict[str, Any]:
        """Return layer statistics (backward-compatible)."""
        return {"in": self.in_dim, "out": self.out_dim, "grid": self.grid_size}


class KAN:
    """Full Kolmogorov-Arnold Network.

    Features:
    - Multi-layer KAN composition
    - B-spline activations per edge
    - Training simulation
    - Symbolic regression attempt
    """

    def __init__(self, layers: list[int]) -> None:
        self.layers: list[KANLayer] = [
            KANLayer(layers[i], layers[i + 1]) for i in range(len(layers) - 1)
        ]
        self.layer_sizes = layers
        self._trained: bool = False

    def forward(self, x: list[float]) -> list[float]:
        """Forward pass through KAN (backward-compatible)."""
        current = x
        for layer in self.layers:
            current = layer.forward(current)
        return current

    def train(
        self,
        inputs: list[list[float]],
        targets: list[list[float]],
        epochs: int = 100,
        lr: float = 0.01,
    ) -> dict[str, Any]:
        """Simulate training."""
        loss = 1.0
        for _epoch in range(epochs):
            # Simulate gradient descent
            loss = max(0.01, loss * 0.99)
            for layer in self.layers:
                gradients = [
                    random.gauss(0, 0.1) for _ in range(len(layer.coefficients))
                ]
                layer.update_coefficients(gradients, lr)
        self._trained = True
        return {"epochs": epochs, "final_loss": round(loss, 4), "trained": True}

    def symbolic_regression(self) -> list[str]:
        """Attempt to extract symbolic formulas from trained KAN."""
        formulas = []
        for layer in self.layers:
            for coeff_idx, coeffs in enumerate(layer.coefficients):
                # Check if coefficients are close to known functions
                mean_coeff = sum(coeffs) / len(coeffs)
                if abs(mean_coeff) < 0.01:
                    formulas.append("0")
                elif abs(max(coeffs) - min(coeffs)) < 0.05:
                    formulas.append(f"x * {round(mean_coeff, 2)}")
                else:
                    formulas.append(f"spline_{coeff_idx}")
        return formulas

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        return {
            "layers": len(self.layers),
            "layer_sizes": self.layer_sizes,
            "total_edges": sum(l.in_dim * l.out_dim for l in self.layers),
            "trained": self._trained,
        }
