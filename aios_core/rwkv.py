"""RWKV (Receptance Weighted Key Value) for AIOS v10.10.0.

RWKV architecture: time-mixing (WKV state), channel-mixing,
token-shift, group normalization, recurrence mode, and
linear attention approximation.

Classes:
    WKVState    — weighted key-value state tracker
    RWKVBlock   — time-mix + channel-mix block
    RWKV        — full RWKV stack
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class WKVState:
    """Weighted key-value state for time-mixing."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.wkv = [0.0] * dim
        self._decay = 0.9
        self._bonus = 0.1

    def update(self, k: list[float], v: list[float]) -> list[float]:
        """WKV update: wkv = decay * wkv + bonus * k * v."""
        self.wkv = [
            d * self._decay + self._bonus * ki * vi for d, ki, vi in zip(self.wkv, k, v, strict=False)
        ]
        return list(self.wkv)

    def set_decay(self, decay: float, bonus: float = 0.1) -> None:
        """Update decay/bonus parameters."""
        self._decay = decay
        self._bonus = bonus

    def reset(self) -> None:
        """Reset WKV state."""
        self.wkv = [0.0] * self.dim

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "decay": self._decay, "bonus": self._bonus}


class RWKVBlock:
    """RWKV block: time-mixing + channel-mixing."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.wkv_state = WKVState(dim)
        self._time_mix_weights = [random.gauss(0, 0.02) for _ in range(dim)]
        self._channel_mix_weights = [random.gauss(0, 0.02) for _ in range(dim)]
        self._receptance = [random.gauss(0, 0.02) for _ in range(dim)]

    def _token_shift(
        self, x: list[float], prev: list[float], ratio: float = 0.5
    ) -> list[float]:
        """Token shift: blend current with previous."""
        return [xi * ratio + pi * (1 - ratio) for xi, pi in zip(x, prev, strict=False)]

    def _group_norm(self, x: list[float], groups: int = 4) -> list[float]:
        """Group normalization."""
        chunk_size = max(1, len(x) // groups)
        result: list[float] = []
        for g in range(groups):
            chunk = x[g * chunk_size : (g + 1) * chunk_size]
            if not chunk:
                continue
            mean = sum(chunk) / len(chunk)
            var = sum((v - mean) ** 2 for v in chunk) / len(chunk)
            result.extend([(v - mean) / math.sqrt(var + 1e-6) for v in chunk])
        return result[: len(x)]

    def _sigmoid(self, x: list[float]) -> list[float]:
        return [1.0 / (1.0 + math.exp(-max(-10, min(10, v)))) for v in x]

    def time_mixing(
        self, x: list[float], prev: list[float] | None = None
    ) -> list[float]:
        """Time-mixing sub-layer (backward-compatible)."""
        prev = prev or [0.0] * self.dim
        shifted = self._token_shift(x, prev)
        k = [si * w for si, w in zip(shifted, self._time_mix_weights, strict=False)]
        v = [si * w for si, w in zip(shifted, self._time_mix_weights, strict=False)]
        wkv = self.wkv_state.update(k, v)
        # Receptance gate
        r = self._sigmoid([si * w for si, w in zip(shifted, self._receptance, strict=False)])
        return [ri * wi for ri, wi in zip(r, wkv, strict=False)]

    def channel_mixing(
        self, x: list[float], prev: list[float] | None = None
    ) -> list[float]:
        """Channel-mixing sub-layer."""
        prev = prev or [0.0] * self.dim
        shifted = self._token_shift(x, prev, ratio=0.7)
        # Squared ReLU (RWKV channel-mixing activation)
        mixed = [
            max(0, si * w) ** 2 for si, w in zip(shifted, self._channel_mix_weights, strict=False)
        ]
        r = self._sigmoid([si * w for si, w in zip(shifted, self._receptance, strict=False)])
        return [ri * mi for ri, mi in zip(r, mixed, strict=False)]

    def forward(self, x: list[float]) -> list[float]:
        """Full block forward (backward-compatible)."""
        # Time-mixing
        time_out = self.time_mixing(x)
        # Channel-mixing on time-mixing output
        chan_out = self.channel_mixing(time_out)
        # Group norm
        return self._group_norm(chan_out)

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "wkv": self.wkv_state.stats()}


class RWKV:
    """RWKV architecture (RNN-like Transformer alternative)."""

    def __init__(self, layers: int = 12, dim: int = 512) -> None:
        self.blocks = [RWKVBlock(dim) for _ in range(layers)]
        self._prev_outputs: list[list[float] | None] = [None] * layers

    def forward(self, x: list[float]) -> list[float]:
        """Forward pass through all blocks (backward-compatible)."""
        for i, block in enumerate(self.blocks):
            prev = self._prev_outputs[i]
            x = block.time_mixing(x, prev)
            x = block.channel_mixing(x, prev)
            self._prev_outputs[i] = x[:]
        return x

    def reset(self) -> None:
        """Reset all block states for new sequence."""
        for block in self.blocks:
            block.wkv_state.reset()
        self._prev_outputs = [None] * len(self.blocks)

    def stats(self) -> dict[str, Any]:
        return {
            "layers": len(self.blocks),
            "dim": self.blocks[0].dim if self.blocks else 0,
        }
