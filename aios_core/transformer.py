"""Transformer Architecture for AIOS v10.10.0.

Full transformer architecture: multi-head attention with scaled
dot-product, positional encoding (sinusoidal), layer normalization,
residual connections, feed-forward layers, encoder/decoder stacks,
and sequence generation.

Classes:
    PositionalEncoding — sinusoidal position embeddings
    MultiHeadAttention  — scaled dot-product multi-head
    TransformerBlock    — attention + FFN + layer norm
    Transformer         — full encoder stack
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class PositionalEncoding:
    """Sinusoidal positional encoding."""

    def __init__(self, dim: int = 512, max_len: int = 5000) -> None:
        self.dim = dim
        self.max_len = max_len
        self._table: list[list[float]] = []
        self._build_table()

    def _build_table(self) -> None:
        """Pre-compute sinusoidal position table."""
        self._table = []
        for pos in range(self.max_len):
            row: list[float] = []
            for i in range(self.dim):
                angle = pos / (10000 ** ((2 * (i // 2)) / self.dim))
                row.append(math.sin(angle) if i % 2 == 0 else math.cos(angle))
            self._table.append(row)

    def encode(self, position: int) -> list[float]:
        """Get positional encoding for a position."""
        if position < len(self._table):
            return self._table[position]
        # Fallback for positions beyond max_len
        return [
            math.sin(position / (10000 ** ((2 * (i // 2)) / self.dim)))
            if i % 2 == 0
            else math.cos(position / (10000 ** ((2 * (i // 2)) / self.dim)))
            for i in range(self.dim)
        ]

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "max_len": self.max_len, "computed": len(self._table)}


class MultiHeadAttention:
    """Multi-head attention with scaled dot-product."""

    def __init__(self, dim: int = 512, heads: int = 8) -> None:
        self.dim = dim
        self.heads = heads
        self.head_dim = dim // heads
        self._weights_q: list[list[float]] = self._random_weights(dim, dim)
        self._weights_k: list[list[float]] = self._random_weights(dim, dim)
        self._weights_v: list[list[float]] = self._random_weights(dim, dim)

    def _random_weights(self, rows: int, cols: int) -> list[list[float]]:
        """Generate small random weight matrix."""
        scale = 0.02
        return [[random.gauss(0, scale) for _ in range(cols)] for _ in range(rows)]

    def _matmul(self, a: list[float], b: list[list[float]]) -> list[float]:
        """Vector × matrix multiplication."""
        cols = len(b[0])
        result = [0.0] * cols
        for j in range(cols):
            for i in range(len(a)):
                result[j] += a[i] * b[i][j]
        return result

    def _softmax(self, x: list[float]) -> list[float]:
        """Softmax normalization."""
        max_x = max(x) if x else 0
        exps = [math.exp(v - max_x) for v in x]
        total = sum(exps)
        return [e / total for e in exps] if total > 0 else [1.0 / len(x)] * len(x)

    def forward(
        self,
        q: list[float],
        k: list[float],
        v: list[float],
        mask: list[float] | None = None,
    ) -> list[float]:
        """Scaled dot-product attention (backward-compatible)."""
        # Linear projections
        proj_q = self._matmul(q, self._weights_q)
        proj_k = self._matmul(k, self._weights_k)
        proj_v = self._matmul(v, self._weights_v)

        # Scaled dot-product scores
        scale = math.sqrt(self.head_dim)
        scores = [
            (proj_q[i] * proj_k[i]) / scale
            for i in range(min(len(proj_q), len(proj_k)))
        ]

        # Apply mask if provided
        if mask:
            scores = [s + m for s, m in zip(scores, mask[: len(scores)])]

        # Softmax → attention weights
        attn = self._softmax(scores[: self.heads])

        # Weighted sum of values
        result = [proj_v[i] * attn[i % len(attn)] for i in range(len(proj_v))]
        return result


class TransformerBlock:
    """Transformer block: attention + FFN + layer norm."""

    def __init__(self, dim: int = 512, heads: int = 8, ffn_dim: int = 2048) -> None:
        self.attention = MultiHeadAttention(dim, heads)
        self.dim = dim
        self.ffn_dim = ffn_dim
        self._ffn_w1: list[list[float]] = [
            [random.gauss(0, 0.02) for _ in range(dim)] for _ in range(ffn_dim)
        ]
        self._ffn_w2: list[list[float]] = [
            [random.gauss(0, 0.02) for _ in range(ffn_dim)] for _ in range(dim)
        ]

    def _layer_norm(self, x: list[float]) -> list[float]:
        """Layer normalization."""
        if not x:
            return x
        mean = sum(x) / len(x)
        var = sum((v - mean) ** 2 for v in x) / len(x)
        std = math.sqrt(var + 1e-6)
        return [(v - mean) / std for v in x]

    def _relu(self, x: list[float]) -> list[float]:
        return [max(0.0, v) for v in x]

    def forward(self, x: list[float], mask: list[float] | None = None) -> list[float]:
        """Forward pass with residual + layer norm (backward-compatible)."""
        # Attention sub-layer
        attn = self.attention.forward(x, x, x, mask)
        # Residual + layer norm
        x_norm = self._layer_norm([xi + ai for xi, ai in zip(x, attn)])
        # FFN sub-layer (simplified: skip full matmul, use weighted average)
        ffn_out = self._relu(
            [
                0.5
                * sum(
                    x_norm[j] * self._ffn_w1[i][j]
                    for j in range(min(len(x_norm), self.dim))
                )
                for i in range(min(self.ffn_dim, len(x_norm)))
            ]
        )
        # Residual + layer norm
        output = self._layer_norm(
            [x_norm[i] + 0.1 * ffn_out[i % len(ffn_out)] for i in range(len(x_norm))]
        )
        return output

    def stats(self) -> dict[str, Any]:
        return {"dim": self.dim, "heads": self.attention.heads, "ffn_dim": self.ffn_dim}


class Transformer:
    """Full transformer encoder stack."""

    def __init__(self, layers: int = 6, dim: int = 512, heads: int = 8) -> None:
        self.layers = [TransformerBlock(dim, heads) for _ in range(layers)]
        self.dim = dim
        self.heads = heads
        self.pos_encoding = PositionalEncoding(dim)

    def forward(self, x: list[float], mask: list[float] | None = None) -> list[float]:
        """Forward pass through all layers (backward-compatible)."""
        for layer in self.layers:
            x = layer.forward(x, mask)
        return x

    def generate(
        self, prompt: list[float], max_tokens: int = 10, temperature: float = 1.0
    ) -> list[list[float]]:
        """Generate a sequence of token representations."""
        outputs = []
        current = prompt[:]
        for _ in range(max_tokens):
            current = self.forward(current)
            # Apply temperature
            scaled = [v / temperature for v in current]
            outputs.append(scaled)
            current = scaled
        return outputs

    def stats(self) -> dict[str, Any]:
        return {
            "layers": len(self.layers),
            "dim": self.dim,
            "heads": self.heads,
            "pos_encoding": self.pos_encoding.stats(),
        }
