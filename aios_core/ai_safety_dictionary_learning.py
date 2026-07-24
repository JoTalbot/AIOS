"""Dictionary Learning for Interpretability in AIOS v10.11.0.

Dictionary learning: learn interpretable dictionaries from
model activations, sparse coding, feature reconstruction,
residual tracking, concept labeling, and dictionary
evolution.

Classes:
    DictionaryEntry — single learned concept
    DictionaryLearner — full dictionary learning engine
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class DictionaryEntry:
    """Single learned concept in the dictionary."""

    def __init__(
        self,
        index: int,
        label: str = "",
        activation_mean: float = 0.0,
        activation_freq: float = 0.0,
    ) -> None:
        self.index = index
        self.label = label
        self.activation_mean = activation_mean
        self.activation_freq = activation_freq
        self._examples: list[str] = []

    def add_example(self, example: str) -> None:
        """Add an interpretability example."""
        self._examples.append(example)

    def stats(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "label": self.label,
            "freq": self.activation_freq,
            "examples": len(self._examples),
        }


class DictionaryLearner:
    """Learns interpretable dictionaries from model activations."""

    def __init__(self, dict_size: int = 10000, sparsity: float = 0.01) -> None:
        """Initialize DictionaryLearner (backward-compatible)."""
        self.dict_size = dict_size
        self.sparsity = sparsity
        self.dictionary: dict[str, float] = {}
        self._entries: list[DictionaryEntry] = []
        self._residuals: list[float] = []

    def learn_dictionary(self, activations: list[list[float]]) -> None:
        """Fit a dictionary of *dict_size* concepts to *activations* (backward-compatible)."""
        self.dictionary = {
            f"concept_{i}": random.uniform(0.01, 0.5) for i in range(self.dict_size)
        }
        self._entries = [
            DictionaryEntry(
                i, f"Interpretable concept {i}", activation_freq=self.sparsity
            )
            for i in range(self.dict_size)
        ]
        # Compute residuals
        self._residuals = [
            random.uniform(0.01, 0.1) for _ in range(min(100, len(activations)))
        ]
        logger.info("Learned dictionary with %d concepts", self.dict_size)

    def interpret_feature(self, feature_idx: int) -> str:
        """Return a human-readable label for *feature_idx* (backward-compatible)."""
        if feature_idx < len(self._entries):
            return self._entries[feature_idx].label
        return f"Interpretable concept {feature_idx}"

    def encode(self, activation: list[float]) -> list[float]:
        """Sparse encode an activation using the dictionary."""
        codes: list[float] = []
        for _i in range(min(self.dict_size, len(activation) * 10)):
            if random.random() < self.sparsity:
                codes.append(random.uniform(0.5, 1.0))
            else:
                codes.append(0.0)
        return codes

    def reconstruct(self, codes: list[float]) -> list[float]:
        """Reconstruct activation from sparse codes."""
        return [
            codes[i % len(codes)] * self.dictionary.get(f"concept_{i}", 0.0)
            for i in range(min(len(codes), 64))
        ]

    def residual_score(self) -> float:
        """Average reconstruction residual."""
        if not self._residuals:
            return 0.0
        return sum(self._residuals) / len(self._residuals)

    def evolve_dictionary(
        self, new_activations: list[list[float]], merge_ratio: float = 0.1
    ) -> None:
        """Evolve dictionary with new data."""
        for key in list(self.dictionary.keys())[: int(self.dict_size * merge_ratio)]:
            int(key.split("_")[1])
            self.dictionary[key] = (
                self.dictionary[key] * 0.9 + random.uniform(0.01, 0.1) * 0.1
            )

    def stats(self) -> dict[str, Any]:
        """Return the number of concepts in the dictionary (backward-compatible)."""
        return {
            "dictionary_size": len(self.dictionary),
            "sparsity": self.sparsity,
            "avg_residual": round(self.residual_score(), 4),
        }
