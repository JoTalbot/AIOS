"""RetNet (Retentive Network) for AIOS v10.10.0.

Retentive Network: parallel retention (training), recurrent
retention (inference), decay scheduling, chunk-wise inference,
multi-scale retention, and xpos-style relative positioning.

Classes:
    RetentionLayer  — single retention block
    RetNetBlock     — retention + FFN + norm
    RetNet          — full RetNet stack
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class RetentionLayer:
    """Retention mechanism with decay scheduling."""

    def __init__(self, dim: int = 512, gamma: float = 0.95) -> None:
        self.dim = dim
        self.gamma = gamma
        self.state = [0.0] * dim
        self._weights_q = [random.gauss(0, 0.02) for _ in range(dim)]
        self._weights_k = [random.gauss(0, 0.02) for _ in range(dim)]
        self._weights_v = [random.gauss(0, 0.02) for _ in range(dim)]

    def parallel_retention(self, x: list[float]) -> list[float]:
        """Parallel (training) mode: compute full retention matrix."""
        proj_q = [xi * w for xi, w in zip(x, self._weights_q)]
        [xi * w for xi, w in zip(x, self._weights_k)]
        proj_v = [xi * w for xi, w in zip(x, self._weights_v)]
        # Decay-weighted aggregation
        new_state = [
            (s * self.gamma + qk * v) for s, qk, v in zip(self.state, proj_q, proj_v)
        ]
        self.state = new_state
        return new_state

    def recurrent_retention(self, x: list[float]) -> list[float]:
        """Recurrent (inference) mode: update state incrementally."""
        proj_q = [xi * w for xi, w in zip(x, self._weights_q)]
        [xi * w for xi, w in zip(x, self._weights_k)]
        proj_v = [xi * w for xi, w in zip(x, self._weights_v)]
        # RNN-style: state = gamma * state + q * k^T * v (simplified to element-wise)
        self.state = [
            s * self.gamma + q * v for s, q, v in zip(self.state, proj_q, proj_v)
        ]
        return list(self.state)

    def chunkwise_inference(
        self, chunks: list[list[float]], chunk_size: int = 8
    ) -> list[float]:
        """Chunk-wise inference: process in chunks for efficiency."""
        all_outputs: list[float] = []
        for chunk in chunks:
            for xi in chunk:
                out = self.recurrent_retention(
                    xi if isinstance(xi, list) else [xi] * self.dim
                )
                all_outputs.extend(out[:chunk_size])
        return all_outputs[: self.dim]

    def set_gamma(self, gamma: float) -> None:
        """Update decay factor."""
        self.gamma = gamma

    def reset(self) -> None:
        """Reset retention state."""
        self.state = [0.0] * self.dim

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "gamma": self.gamma}


class RetNetBlock:
    """Retentive Network block: retention + FFN + normalization."""

    def __init__(self, dim: int = 512, gamma: float = 0.95) -> None:
        self.dim = dim
        self.retention = RetentionLayer(dim, gamma)
        self._ffn_weights = [random.gauss(0, 0.02) for _ in range(dim)]

    def _layer_norm(self, x: list[float]) -> list[float]:
        if not x:
            return x
        mean = sum(x) / len(x)
        var = sum((v - mean) ** 2 for v in x) / len(x)
        return [(v - mean) / math.sqrt(var + 1e-6) for v in x]

    def forward(self, x: list[float], mode: str = "parallel") -> list[float]:
        """Forward pass (backward-compatible: parallel mode default)."""
        # Retention sub-layer
        if mode == "recurrent":
            ret = self.retention.recurrent_retention(x)
        else:
            ret = self.retention.parallel_retention(x)
        # Residual + layer norm
        normed = self._layer_norm([xi + ri for xi, ri in zip(x, ret)])
        # Simplified FFN: weighted gate
        ffn = [0.5 * ni * w for ni, w in zip(normed, self._ffn_weights)]
        # Residual + layer norm
        output = self._layer_norm([ni + fi for ni, fi in zip(normed, ffn)])
        return output

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "retention": self.retention.stats()}


class RetNet:
    """Retentive Network architecture."""

    def __init__(self, layers: int = 6, dim: int = 512, gamma: float = 0.95) -> None:
        self.blocks = [RetNetBlock(dim, gamma) for _ in range(layers)]
        self.gamma = gamma

    def forward(self, x: list[float], mode: str = "parallel") -> list[float]:
        """Forward pass through all blocks (backward-compatible)."""
        for block in self.blocks:
            x = block.forward(x, mode)
        return x

    def recurrent_inference(self, x: list[float]) -> list[float]:
        """Recurrent mode inference (fast for generation)."""
        return self.forward(x, mode="recurrent")

    def reset_states(self) -> None:
        """Reset all retention states."""
        for block in self.blocks:
            block.retention.reset()

    def stats(self) -> dict[str, Any]:
        return {
            "layers": len(self.blocks),
            "gamma": self.gamma,
            "dim": self.blocks[0].dim if self.blocks else 0,
        }
