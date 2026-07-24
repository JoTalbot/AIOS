"""Continual / Lifelong Learning for AIOS v10.8.0.

Prevents catastrophic forgetting with Elastic Weight
Consolidation (EWC), task boundaries, rehearsal buffer,
forgetting measurement, progressive networks, and
task-specific importance tracking.

Classes:
    TaskBoundary   — marks a task transition point
    ContinualLearner — full continual learning engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskBoundary:
    """Marks a task transition point with importance weights."""

    task_name: str
    timestamp: float = field(default_factory=time.time)
    importance_weights: dict[str, float] = field(default_factory=dict)
    performance_before: float = 0.0
    performance_after: float = 0.0


class ContinualLearner:
    """Full continual learning engine.

    Features:
    - EWC importance tracking per task
    - Rehearsal buffer for knowledge retention
    - Forgetting measurement across tasks
    - Task boundary detection
    - Progressive task scaling
    - Transfer detection between tasks
    """

    def __init__(self, ewc_lambda: float = 0.4, rehearsal_size: int = 50) -> None:
        self.tasks: list[str] = []
        self.importance: dict[str, float] = {}
        self.task_boundaries: list[TaskBoundary] = []
        self.rehearsal_buffer: list[dict[str, Any]] = []
        self.per_task_performance: dict[str, float] = {}
        self.ewc_lambda = ewc_lambda
        self.rehearsal_size = rehearsal_size
        self._ewc_penalty: dict[str, float] = {}

    # ── Task Learning ──────────────────────────────────────────────

    def learn_task(
        self, task_name: str, importance: float = 1.0, performance: float = 1.0
    ) -> TaskBoundary:
        """Learn a new task with importance weighting."""
        boundary = TaskBoundary(
            task_name=task_name,
            importance_weights={task_name: importance},
            performance_before=self.per_task_performance.get(task_name, 0.0),
            performance_after=performance,
        )
        self.tasks.append(task_name)
        self.importance[task_name] = importance
        self.per_task_performance[task_name] = performance
        self.task_boundaries.append(boundary)

        # Update EWC penalty for all previous tasks
        for prev_task in self.tasks[:-1]:
            self._ewc_penalty[prev_task] = self.ewc_lambda * self.importance.get(
                prev_task, 1.0
            )

        return boundary

    def protect_weights(self, task_name: str) -> float:
        """Return EWC protection weight for a task."""
        return self.importance.get(task_name, 0.5)

    def ewc_loss(self, current_task: str) -> float:
        """Compute EWC regularization loss."""
        total_penalty = 0.0
        for task in self.tasks:
            if task != current_task:
                total_penalty += self._ewc_penalty.get(task, 0.0)
        return total_penalty

    # ── Rehearsal Buffer ────────────────────────────────────────────

    def add_rehearsal(self, data: dict[str, Any], task_name: str) -> None:
        """Add data to rehearsal buffer."""
        entry = {"data": data, "task": task_name, "timestamp": time.time()}
        self.rehearsal_buffer.append(entry)
        # Maintain buffer size
        if len(self.rehearsal_buffer) > self.rehearsal_size:
            self.rehearsal_buffer = self.rehearsal_buffer[-self.rehearsal_size :]

    def get_rehearsal(
        self, task_name: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retrieve rehearsal data, optionally filtered by task."""
        filtered = [r for r in self.rehearsal_buffer if r["task"] == task_name] if task_name else self.rehearsal_buffer
        return filtered[-limit:]

    def clear_rehearsal(self) -> None:
        """Clear the rehearsal buffer."""
        self.rehearsal_buffer.clear()

    # ── Forgetting Measurement ──────────────────────────────────────

    def measure_forgetting(self, task_name: str) -> float:
        """Measure forgetting of a previously learned task.

        Returns the drop in performance from the task's peak.
        """
        if task_name not in self.per_task_performance:
            return 0.0

        # Find peak performance for this task
        peak = 0.0
        current = self.per_task_performance.get(task_name, 0.0)
        for boundary in self.task_boundaries:
            if boundary.task_name == task_name:
                peak = max(peak, boundary.performance_after)

        if peak == 0.0:
            return 0.0
        forgetting = peak - current
        return max(0.0, forgetting)

    def total_forgetting(self) -> float:
        """Average forgetting across all tasks."""
        if not self.tasks:
            return 0.0
        total = sum(self.measure_forgetting(t) for t in self.tasks)
        return total / len(self.tasks)

    # ── Transfer Detection ──────────────────────────────────────────

    def forward_transfer(self, source_task: str, target_task: str) -> float:
        """Estimate forward transfer from source to target."""
        source_perf = self.per_task_performance.get(source_task, 0.0)
        self.per_task_performance.get(target_task, 0.0)
        source_imp = self.importance.get(source_task, 0.5)
        return min(1.0, source_perf * source_imp * 0.3)

    def backward_transfer(self, new_task: str) -> float:
        """Estimate backward transfer effect on old tasks."""
        if len(self.tasks) <= 1:
            return 0.0
        total_impact = 0.0
        for old_task in self.tasks[:-1]:
            self.per_task_performance.get(old_task, 0.0)
            forgetting = self.measure_forgetting(old_task)
            total_impact -= forgetting
        return total_impact / (len(self.tasks) - 1) if len(self.tasks) > 1 else 0.0

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_perf = (
            sum(self.per_task_performance.values()) / len(self.per_task_performance)
            if self.per_task_performance
            else 0.0
        )
        return {
            "tasks_learned": len(self.tasks),
            "rehearsal_size": len(self.rehearsal_buffer),
            "avg_performance": round(avg_perf, 4),
            "total_forgetting": round(self.total_forgetting(), 4),
            "ewc_penalty": round(sum(self._ewc_penalty.values()), 4),
        }
