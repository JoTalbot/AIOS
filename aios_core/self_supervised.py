"""Self-Supervised Learning for AIOS v10.8.0.

Self-supervised pretraining with contrastive learning,
augmentation pipeline, representation quality metrics,
pretext task selection, NT-Xent loss, and projection
head simulation.

Classes:
    PretextTask    — pretext task definition
    Augmentation   — data augmentation specification
    SelfSupervisedLearner — full self-supervised engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PretextTask:
    """Pretext task definition."""
    name: str
    description: str = ""
    difficulty: float = 0.5  # 0..1
    representation_quality: float = 0.0
    success_rate: float = 0.0
    augmentation_type: str = "default"


@dataclass
class Augmentation:
    """Data augmentation specification."""
    name: str
    intensity: float = 0.5  # 0..1
    probability: float = 0.5  # 0..1
    parameters: dict[str, Any] = field(default_factory=dict)


class SelfSupervisedLearner:
    """Full self-supervised learning engine.

    Features:
    - Pretext task management (rotation, colorization, jigsaw, contrastive)
    - Augmentation pipeline
    - Contrastive loss (NT-Xent)
    - Pseudo-label generation
    - Representation quality metrics
    - Projection head simulation
    - Linear evaluation protocol
    """

    def __init__(self, temperature: float = 0.5) -> None:
        self.pretext_tasks: list[str] = ["rotation", "colorization", "jigsaw", "contrastive"]
        self.task_configs: dict[str, PretextTask] = {}
        self.augmentations: list[Augmentation] = []
        self.temperature = temperature
        self._representation_dim: int = 512
        self._projection_dim: int = 128
        self._loss_history: list[float] = []

        # Initialize pretext task configs
        for name in self.pretext_tasks:
            self.task_configs[name] = PretextTask(name=name, difficulty=random.uniform(0.3, 0.7))

    # ── Pseudo-Label Generation ──────────────────────────────────────

    def generate_pseudo_label(self, data: Any, task: str = "rotation") -> Any:
        """Generate pseudo label for a pretext task."""
        if task == "rotation":
            return random.choice([0, 90, 180, 270])
        elif task == "colorization":
            return random.choice(["grayscale", "sepia", "normal"])
        elif task == "jigsaw":
            return random.randint(0, 9)  # 9 permutation groups
        elif task == "contrastive":
            return 1  # positive pair label
        return "pseudo_label"

    def generate_batch_pseudo_labels(self, data_list: list[Any],
                                      task: str = "rotation") -> list[Any]:
        """Generate pseudo labels for a batch of data."""
        return [self.generate_pseudo_label(d, task) for d in data_list]

    # ── Contrastive Learning ─────────────────────────────────────────

    def contrastive_loss(self, embeddings: list[list[float]]) -> float:
        """Compute NT-Xent (Normalized Temperature-scaled Cross Entropy) loss."""
        if len(embeddings) < 2:
            return 0.0

        # Pairwise cosine similarities
        n = len(embeddings)
        total_loss = 0.0
        pairs = 0

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                # NT-Xent: -log(exp(sim/T) / sum_k exp(sim_k/T))
                numerator = math.exp(sim / self.temperature)
                denominator = numerator
                for k in range(n):
                    if k != i:
                        denominator += math.exp(self._cosine_similarity(embeddings[i], embeddings[k]) / self.temperature)

                if denominator > 0:
                    total_loss -= math.log(numerator / denominator)
                pairs += 1

        avg_loss = total_loss / max(pairs, 1)
        self._loss_history.append(avg_loss)
        return avg_loss

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        min_len = min(len(a), len(b))
        a_trunc = a[:min_len]
        b_trunc = b[:min_len]
        dot = sum(x * y for x, y in zip(a_trunc, b_trunc))
        na = math.sqrt(sum(x * x for x in a_trunc))
        nb = math.sqrt(sum(y * y for y in b_trunc))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    # ── Augmentation Pipeline ────────────────────────────────────────

    def add_augmentation(self, name: str, intensity: float = 0.5,
                         probability: float = 0.5) -> Augmentation:
        """Add an augmentation to the pipeline."""
        aug = Augmentation(name=name, intensity=intensity, probability=probability)
        self.augmentations.append(aug)
        return aug

    def augment(self, data: list[float], augmentations: list[Augmentation] | None = None) -> list[float]:
        """Apply augmentation pipeline to data."""
        augs = augmentations or self.augmentations
        result = data[:]

        for aug in augs:
            if random.random() < aug.probability:
                # Apply augmentation
                if aug.name == "noise":
                    result = [v + random.gauss(0, aug.intensity * 0.1) for v in result]
                elif aug.name == "scale":
                    result = [v * random.uniform(1 - aug.intensity, 1 + aug.intensity) for v in result]
                elif aug.name == "mask":
                    # Randomly mask some values
                    result = [v if random.random() > aug.intensity else 0.0 for v in result]
                elif aug.name == "crop":
                    # Random crop
                    start = random.randint(0, len(result) // 2)
                    end = start + len(result) // 2
                    result = result[start:end]
                elif aug.name == "flip":
                    result = result[::-1]
                else:
                    # Generic: add noise proportional to intensity
                    result = [v + random.gauss(0, aug.intensity * 0.05) for v in result]

        return result

    def create_augmented_pair(self, data: list[float]) -> tuple[list[float], list[float]]:
        """Create two augmented views of the same data (for contrastive learning)."""
        view1 = self.augment(data)
        view2 = self.augment(data)
        return view1, view2

    # ── Projection Head ──────────────────────────────────────────────

    def project(self, embedding: list[float]) -> list[float]:
        """Simulate projection head: map embedding to projection space."""
        if len(embedding) <= self._projection_dim:
            return embedding[:self._projection_dim]

        # Simple projection: take every nth element + random mixing
        step = len(embedding) // self._projection_dim
        projected = embedding[::step][:self._projection_dim]
        # Add some nonlinearity
        projected = [math.tanh(p) for p in projected]
        return projected

    # ── Representation Quality ────────────────────────────────────────

    def representation_quality(self, representations: list[list[float]]) -> dict[str, Any]:
        """Evaluate representation quality."""
        if not representations:
            return {"alignment": 0.0, "uniformity": 0.0}

        # Alignment: average cosine similarity between positive pairs
        alignment = 0.0
        if len(representations) >= 2:
            for i in range(len(representations) - 1):
                alignment += self._cosine_similarity(representations[i], representations[i + 1])
            alignment = alignment / (len(representations) - 1)

        # Uniformity: average pairwise distance (should be spread out)
        uniformity = 0.0
        if len(representations) >= 2:
            distances = []
            for i in range(len(representations)):
                for j in range(i + 1, len(representations)):
                    sim = self._cosine_similarity(representations[i], representations[j])
                    distances.append(1 - sim)
            uniformity = sum(distances) / len(distances) if distances else 0.0

        return {
            "alignment": round(alignment, 4),
            "uniformity": round(uniformity, 4),
            "num_representations": len(representations),
        }

    # ── Linear Evaluation ────────────────────────────────────────────

    def linear_eval(self, representations: list[list[float]],
                    labels: list[int]) -> float:
        """Simulate linear evaluation accuracy."""
        if not representations or not labels:
            return 0.0

        # Higher alignment and diversity → better linear eval
        quality = self.representation_quality(representations)
        base_acc = 0.5 + quality["alignment"] * 0.3 + quality["uniformity"] * 0.2
        return round(min(0.99, base_acc), 4)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_loss = sum(self._loss_history) / len(self._loss_history) if self._loss_history else 0.0
        return {
            "pretext_tasks": len(self.pretext_tasks),
            "augmentations": len(self.augmentations),
            "representation_dim": self._representation_dim,
            "projection_dim": self._projection_dim,
            "avg_loss": round(avg_loss, 4),
            "temperature": self.temperature,
        }
