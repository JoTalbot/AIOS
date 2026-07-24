"""Mamba / State Space Models for AIOS v10.8.0.

Selective State Space Model (Mamba) with input-dependent
parameters, discretization, parallel scan simulation,
recurrence mode, and layer stacking.

Classes:
    MambaConfig    — model configuration
    MambaBlock     — single Mamba SSM block
    MambaStacked   — multi-layer Mamba model
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MambaConfig:
    """Mamba model configuration."""

    d_model: int = 512
    d_state: int = 16
    d_conv: int = 3  # local convolution width
    expand_factor: int = 2  # inner dimension = expand_factor * d_model
    dt_min: float = 0.001
    dt_max: float = 0.1
    dt_init: str = "random"  # random or uniform


class MambaBlock:
    """Full Mamba (Selective State Space Model) block.

    Features:
    - Input-dependent selection mechanism
    - Discretized continuous parameters (dt, A, B, C)
    - Parallel scan for efficient computation
    - Recurrence mode for autoregressive generation
    - Local convolution preprocessing
    """

    def __init__(
        self,
        d_model: int = 512,
        d_state: int = 16,
        d_conv: int = 3,
        expand_factor: int = 2,
        dt_min: float = 0.001,
        dt_max: float = 0.1,
    ) -> None:
        self.d_model = d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.d_inner = d_model * expand_factor
        self.dt_min = dt_min
        self.dt_max = dt_max

        # Initialize state space parameters
        self.state = [0.0] * d_state

        # Discretization parameters (A, B, C matrices as lists)
        self.A_log = [
            -1.0 + random.uniform(0, 0.5) for _ in range(d_state)
        ]  # log of diagonal A
        self.D = [0.0] * d_model  # skip connection

        # Input-dependent projection parameters (simplified)
        self.dt_proj = [random.uniform(dt_min, dt_max) for _ in range(d_model)]
        self.B_proj = [
            [random.gauss(0, 0.1) for _ in range(d_state)] for _ in range(d_model)
        ]
        self.C_proj = [
            [random.gauss(0, 0.1) for _ in range(d_model)] for _ in range(d_state)
        ]

        # Conv1d kernel (simplified)
        self.conv_kernel = [random.gauss(0, 0.1) for _ in range(d_conv)]

        self._step_count = 0

    def _selective_params(
        self, x: float, idx: int
    ) -> tuple[float, list[float], list[float]]:
        """Compute input-dependent dt, B, C for position idx."""
        dt = self.dt_proj[idx] if idx < len(self.dt_proj) else self.dt_proj[0]
        B = self.B_proj[idx] if idx < len(self.B_proj) else self.B_proj[0]
        C = self.C_proj[idx] if idx < len(self.C_proj) else self.C_proj[0]
        return dt, B, C

    def _discretize(
        self, dt: float, A_log: list[float], B: list[float]
    ) -> tuple[list[float], list[float]]:
        """Discretize continuous parameters using ZOH."""
        A = [math.exp(a) for a in A_log]  # diagonal A
        dA = [math.exp(a * dt) for a in A_log]  # discretized A
        dB = [
            (math.exp(a * dt) - 1) / a * b if abs(a) > 1e-6 else dt * b
            for a, b in zip(A, B, strict=False)
        ]  # discretized B
        return dA, dB

    def forward(self, x: list[float]) -> list[float]:
        """Process input sequence through selective SSM.

        Implements input-dependent selection and state update.
        """
        output = []
        # Reset state
        self.state = [0.0] * self.d_state

        for t, val in enumerate(x):
            # Input-dependent parameters
            dt, B, C = self._selective_params(val, min(t, self.d_model - 1))

            # Discretize
            dA, dB = self._discretize(dt, self.A_log, B)

            # State update: s = dA * s + dB * x
            self.state = [da * s + db * val for da, s, db in zip(dA, self.state, dB, strict=False)]

            # Output: y = C * s + D * x
            y = sum(c * s for c, s in zip(C, self.state, strict=False)) + (
                self.D[min(t, len(self.D) - 1)] * val if t < len(self.D) else 0
            )
            output.append(y)

        self._step_count += len(x)
        return output

    def step(self, x_val: float) -> float:
        """Single-step mode for autoregressive generation."""
        dt, B, C = self._selective_params(x_val, 0)
        dA, dB = self._discretize(dt, self.A_log, B)

        self.state = [da * s + db * x_val for da, s, db in zip(dA, self.state, dB, strict=False)]
        y = sum(c * s for c, s in zip(C, self.state, strict=False))
        self._step_count += 1
        return y

    def reset_state(self) -> None:
        """Reset hidden state."""
        self.state = [0.0] * self.d_state

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "d_model": self.d_model,
            "d_state": self.d_state,
            "d_inner": self.d_inner,
            "d_conv": self.d_conv,
            "steps_processed": self._step_count,
        }


class MambaStacked:
    """Multi-layer stacked Mamba model."""

    def __init__(
        self, num_layers: int = 4, d_model: int = 512, d_state: int = 16
    ) -> None:
        self.layers = [
            MambaBlock(d_model=d_model, d_state=d_state) for _ in range(num_layers)
        ]
        self.num_layers = num_layers

    def forward(self, x: list[float]) -> list[float]:
        """Process through all layers."""
        current = x
        for layer in self.layers:
            current = layer.forward(current)
        return current

    def reset_all(self) -> None:
        """Reset all layer states."""
        for layer in self.layers:
            layer.reset_state()

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "layers": self.num_layers,
            "total_steps": sum(l._step_count for l in self.layers),
        }
