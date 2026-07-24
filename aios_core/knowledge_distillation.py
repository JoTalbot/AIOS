"""Knowledge Distillation for AIOS v10.8.0.

Distills knowledge from large teacher models to smaller
student models with soft targets, temperature scaling,
loss computation, progressive distillation, and model
registry.

Classes:
    ModelConfig    — model configuration descriptor
    DistillationResult — outcome of a distillation run
    KnowledgeDistiller — full distillation engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model configuration descriptor."""

    model_id: str
    model_type: str = "teacher"  # teacher or student
    num_params: int = 0
    accuracy: float = 0.0
    latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class DistillationResult:
    """Outcome of a distillation run."""

    teacher_id: str
    student_id: str
    temperature: float = 2.0
    alpha: float = 0.7  # KD loss weight
    student_accuracy_before: float = 0.0
    student_accuracy_after: float = 0.0
    compression_ratio: float = 0.0
    kd_loss: float = 0.0
    hard_loss: float = 0.0
    total_loss: float = 0.0
    epochs: int = 0
    success: bool = True
    timestamp: float = field(default_factory=time.time)


class KnowledgeDistiller:
    """Full knowledge distillation engine.

    Features:
    - Teacher/student model registry
    - Temperature-scaled soft target generation
    - KD loss + hard loss computation
    - Progressive distillation (multi-stage)
    - Compression ratio tracking
    - Distillation history
    """

    def __init__(self) -> None:
        self.teacher_models: dict[str, ModelConfig] = {}
        self.student_models: dict[str, ModelConfig] = {}
        self.distillation_history: list[DistillationResult] = []

    # ── Model Registry ──────────────────────────────────────────────

    def register_teacher(
        self,
        model_id: str,
        num_params: int = 1000000,
        accuracy: float = 0.95,
        latency_ms: float = 100.0,
    ) -> ModelConfig:
        """Register a teacher model."""
        config = ModelConfig(
            model_id=model_id,
            model_type="teacher",
            num_params=num_params,
            accuracy=accuracy,
            latency_ms=latency_ms,
        )
        self.teacher_models[model_id] = config
        return config

    def register_student(
        self,
        model_id: str,
        num_params: int = 100000,
        accuracy: float = 0.7,
        latency_ms: float = 10.0,
    ) -> ModelConfig:
        """Register a student model."""
        config = ModelConfig(
            model_id=model_id,
            model_type="student",
            num_params=num_params,
            accuracy=accuracy,
            latency_ms=latency_ms,
        )
        self.student_models[model_id] = config
        return config

    def get_teacher(self, model_id: str) -> ModelConfig | None:
        """Return teacher model config."""
        return self.teacher_models.get(model_id)

    def get_student(self, model_id: str) -> ModelConfig | None:
        """Return student model config."""
        return self.student_models.get(model_id)

    # ── Soft Targets ────────────────────────────────────────────────

    def soft_targets(
        self, logits: list[float], temperature: float = 2.0
    ) -> list[float]:
        """Generate temperature-scaled soft targets from logits.

        softmax(z/T) where T is temperature.
        """
        scaled = [logit / temperature for logit in logits]
        # Softmax
        max_val = max(scaled)
        exp_vals = [math.exp(s - max_val) for s in scaled]
        sum_exp = sum(exp_vals)
        return [e / sum_exp for e in exp_vals]

    def hard_targets(self, logits: list[float]) -> list[int]:
        """Generate hard targets (argmax) from logits."""
        if not logits:
            return []
        max_idx = logits.index(max(logits))
        return [1 if i == max_idx else 0 for i in range(len(logits))]

    # ── Loss Computation ────────────────────────────────────────────

    def kd_loss(
        self,
        student_logits: list[float],
        teacher_logits: list[float],
        temperature: float = 2.0,
    ) -> float:
        """Compute knowledge distillation loss (KL divergence).

        L_KD = T^2 * KL(softmax(z_t/T) || softmax(z_s/T))
        """
        teacher_probs = self.soft_targets(teacher_logits, temperature)
        student_probs = self.soft_targets(student_logits, temperature)

        # KL divergence: sum(p_teacher * log(p_teacher / p_student))
        kl = 0.0
        for pt, ps in zip(teacher_probs, student_probs, strict=False):
            if pt > 0 and ps > 0:
                kl += pt * math.log(pt / ps)
            elif pt > 0:
                kl += pt * 10  # large penalty for zero student probability

        return temperature**2 * kl

    def hard_loss(self, student_logits: list[float], true_labels: list[int]) -> float:
        """Compute hard target loss (cross-entropy)."""
        student_probs = self.soft_targets(student_logits, temperature=1.0)
        loss = 0.0
        for sp, tl in zip(student_probs, true_labels, strict=False):
            if tl == 1:
                loss -= math.log(max(sp, 1e-10))
        return loss

    def total_loss(self, kd_loss: float, hard_loss: float, alpha: float = 0.7) -> float:
        """Compute total loss: alpha * KD_loss + (1-alpha) * hard_loss."""
        return alpha * kd_loss + (1 - alpha) * hard_loss

    # ── Distillation ────────────────────────────────────────────────

    def distill(
        self,
        teacher_id: str,
        student_id: str,
        temperature: float = 2.0,
        alpha: float = 0.7,
        epochs: int = 100,
    ) -> DistillationResult:
        """Perform knowledge distillation from teacher to student."""
        if teacher_id not in self.teacher_models:
            return DistillationResult(
                teacher_id=teacher_id,
                student_id=student_id,
                temperature=temperature,
                success=False,
            )

        teacher = self.teacher_models[teacher_id]
        student = self.student_models.get(
            student_id, ModelConfig(model_id=student_id, model_type="student")
        )

        # Simulate distillation
        accuracy_before = student.accuracy
        # Student improves toward teacher accuracy, proportional to epochs
        improvement = (teacher.accuracy - student.accuracy) * min(1.0, epochs / 200)
        accuracy_after = min(teacher.accuracy, accuracy_before + improvement)

        # Compression ratio
        compression = (
            teacher.num_params / student.num_params if student.num_params > 0 else 0.0
        )

        # Simulated losses
        kd_loss_val = max(0.01, 1.0 / (epochs + 1))
        hard_loss_val = max(0.01, 0.5 / (epochs + 1))
        total_loss_val = self.total_loss(kd_loss_val, hard_loss_val, alpha)

        # Update student
        student.accuracy = round(accuracy_after, 4)
        self.student_models[student_id] = student

        result = DistillationResult(
            teacher_id=teacher_id,
            student_id=student_id,
            temperature=temperature,
            alpha=alpha,
            student_accuracy_before=round(accuracy_before, 4),
            student_accuracy_after=round(accuracy_after, 4),
            compression_ratio=round(compression, 2),
            kd_loss=round(kd_loss_val, 4),
            hard_loss=round(hard_loss_val, 4),
            total_loss=round(total_loss_val, 4),
            epochs=epochs,
            success=True,
        )
        self.distillation_history.append(result)
        return result

    def progressive_distill(
        self,
        teacher_id: str,
        student_id: str,
        stages: int = 3,
        temperature_start: float = 4.0,
        temperature_end: float = 1.0,
    ) -> list[DistillationResult]:
        """Progressive distillation with decreasing temperature."""
        results = []
        temp_step = (temperature_start - temperature_end) / stages
        epochs_per_stage = 50

        for stage in range(stages):
            temp = temperature_start - stage * temp_step
            result = self.distill(
                teacher_id, student_id, temperature=temp, epochs=epochs_per_stage
            )
            results.append(result)

        return results

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_teacher_accuracy = (
            (
                sum(t.accuracy for t in self.teacher_models.values())
                / len(self.teacher_models)
            )
            if self.teacher_models
            else 0.0
        )
        avg_student_accuracy = (
            (
                sum(s.accuracy for s in self.student_models.values())
                / len(self.student_models)
            )
            if self.student_models
            else 0.0
        )
        return {
            "teachers": len(self.teacher_models),
            "students": len(self.student_models),
            "distillations": len(self.distillation_history),
            "avg_teacher_accuracy": round(avg_teacher_accuracy, 4),
            "avg_student_accuracy": round(avg_student_accuracy, 4),
        }
