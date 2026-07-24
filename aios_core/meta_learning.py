"""Meta-Learning System for AIOS v10.8.0.

Learns how to learn across different tasks with MAML-like
inner/outer loop, task adaptation tracking, strategy
learning, experience replay, and cross-task transfer.

Classes:
    TaskExperience  — recorded task experience
    AdaptationStep  — single adaptation step result
    MetaLearner     — full meta-learning engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskExperience:
    """Recorded task experience with metadata."""

    task_type: str
    success: bool
    duration: float
    adaptation_steps: int = 0
    initial_loss: float = 0.0
    final_loss: float = 0.0
    strategy_used: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class AdaptationStep:
    """Single adaptation step result."""

    step_number: int
    loss_before: float
    loss_after: float
    learning_rate: float = 0.01
    improvement: float = 0.0


class MetaLearner:
    """Full meta-learning engine.

    Features:
    - Task experience recording and replay
    - Strategy recommendation based on history
    - MAML-like inner loop adaptation
    - Cross-task transfer estimation
    - Learning rate meta-optimization
    - Strategy performance tracking
    """

    def __init__(self, inner_lr: float = 0.01, outer_lr: float = 0.001) -> None:
        self.task_history: list[TaskExperience] = []
        self.strategies: dict[str, float] = {
            "reuse_previous_approach": 1.0,
            "explore_new_approach": 1.0,
            "few_shot_adaptation": 1.0,
            "gradient_based": 1.0,
            "memory_based": 1.0,
        }
        self.strategy_performance: dict[str, list[float]] = {
            "reuse_previous_approach": [],
            "explore_new_approach": [],
            "few_shot_adaptation": [],
            "gradient_based": [],
            "memory_based": [],
        }
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self._adaptation_log: list[AdaptationStep] = []

    # ── Task Recording ──────────────────────────────────────────────

    def record_task(
        self,
        task_type: str,
        success: bool,
        duration: float,
        strategy: str = "",
        initial_loss: float = 0.0,
        final_loss: float = 0.0,
    ) -> TaskExperience:
        """Record a task experience."""
        exp = TaskExperience(
            task_type=task_type,
            success=success,
            duration=duration,
            strategy_used=strategy,
            initial_loss=initial_loss,
            final_loss=final_loss,
        )
        self.task_history.append(exp)

        # Update strategy performance
        if strategy and strategy in self.strategy_performance:
            score = 1.0 if success else 0.0
            self.strategy_performance[strategy].append(score)
            # Update strategy weight (EMA)
            avg = sum(self.strategy_performance[strategy]) / len(
                self.strategy_performance[strategy]
            )
            self.strategies[strategy] = round(avg, 4)

        return exp

    # ── Strategy Recommendation ──────────────────────────────────────

    def recommend_strategy(self, task_type: str) -> str:
        """Recommend the best strategy for a task type."""
        # Check if we have enough history for this task type
        task_experiences = [t for t in self.task_history if t.task_type == task_type]

        if len(task_experiences) >= 3:
            # Find the most successful strategy for this task type
            strategy_counts: dict[str, int] = {}
            for t in task_experiences:
                if t.success and t.strategy_used:
                    strategy_counts[t.strategy_used] = (
                        strategy_counts.get(t.strategy_used, 0) + 1
                    )
            if strategy_counts:
                return max(strategy_counts, key=strategy_counts.get)

        # Use global strategy weights
        return max(self.strategies, key=self.strategies.get)

    def get_strategy_weights(self) -> dict[str, float]:
        """Return current strategy weights."""
        return dict(self.strategies)

    def update_strategy(self, strategy: str, reward: float) -> None:
        """Update a strategy weight based on reward."""
        if strategy in self.strategies:
            current = self.strategies[strategy]
            self.strategies[strategy] = round(
                current + self.outer_lr * (reward - current), 4
            )

    # ── MAML-like Inner Loop ────────────────────────────────────────

    def adapt_inner_loop(
        self, task_type: str, initial_loss: float = 1.0, num_steps: int = 5
    ) -> list[AdaptationStep]:
        """Run inner loop adaptation (few-shot learning on a task)."""
        steps = []
        current_loss = initial_loss

        for step_num in range(num_steps):
            # Simulate loss reduction
            reduction = self.inner_lr * current_loss * random.uniform(0.5, 1.0)
            new_loss = max(0.01, current_loss - reduction)

            step = AdaptationStep(
                step_number=step_num,
                loss_before=round(current_loss, 4),
                loss_after=round(new_loss, 4),
                learning_rate=self.inner_lr,
                improvement=round(current_loss - new_loss, 4),
            )
            steps.append(step)
            self._adaptation_log.append(step)
            current_loss = new_loss

        return steps

    def meta_update(self, task_losses: list[float]) -> float:
        """Run outer loop meta-update across task losses."""
        if not task_losses:
            return 0.0
        avg_loss = sum(task_losses) / len(task_losses)
        # Update meta-learning rate
        self.outer_lr = min(0.01, self.outer_lr * 0.99 + avg_loss * 0.001)
        return round(avg_loss, 4)

    # ── Cross-Task Transfer ─────────────────────────────────────────

    def estimate_transfer(self, source_task: str, target_task: str) -> float:
        """Estimate knowledge transfer between tasks."""
        source_exps = [t for t in self.task_history if t.task_type == source_task]
        if not source_exps:
            return 0.5  # unknown

        success_rate = sum(1 for t in source_exps if t.success) / len(source_exps)
        avg_loss_reduction = sum(
            (t.initial_loss - t.final_loss) for t in source_exps
        ) / len(source_exps)
        transfer = success_rate * 0.6 + min(avg_loss_reduction, 0.5) * 0.4
        return round(transfer, 4)

    def find_similar_tasks(
        self, task_type: str, limit: int = 5
    ) -> list[tuple[str, float]]:
        """Find tasks similar to the given type based on strategy overlap."""
        similarities = []
        for other_type in {t.task_type for t in self.task_history}:
            if other_type == task_type:
                continue
            transfer = self.estimate_transfer(task_type, other_type)
            similarities.append((other_type, transfer))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        success_rate = (
            (sum(1 for t in self.task_history if t.success) / len(self.task_history))
            if self.task_history
            else 0.0
        )
        avg_duration = (
            (sum(t.duration for t in self.task_history) / len(self.task_history))
            if self.task_history
            else 0.0
        )
        return {
            "tasks_learned": len(self.task_history),
            "strategies": len(self.strategies),
            "success_rate": round(success_rate, 4),
            "avg_duration": round(avg_duration, 4),
            "inner_lr": self.inner_lr,
            "outer_lr": self.outer_lr,
            "adaptation_steps": len(self._adaptation_log),
        }
