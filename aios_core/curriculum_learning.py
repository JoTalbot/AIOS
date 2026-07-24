"""Curriculum Learning for AIOS v10.9.0.

Progressive difficulty curriculum with stage management,
automatic progression, difficulty scheduling, mastery
tracking, and adaptive pacing.

Classes:
    CurriculumStage — stage with difficulty and tasks
    Curriculum      — full curriculum engine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CurriculumStage:
    """Stage with difficulty level and tasks."""

    name: str
    difficulty: float = 0.0
    tasks: list[Any] = field(default_factory=list)
    completed: int = 0
    mastery_threshold: int = 5
    started_at: float = 0.0


class Curriculum:
    """Full curriculum learning engine.

    Features:
    - Stage management with difficulty levels
    - Automatic progression based on mastery
    - Difficulty scheduling (linear/exponential)
    - Mastery tracking per stage
    - Adaptive pacing
    - Task sequencing
    """

    def __init__(
        self, mastery_threshold: int = 5, schedule_type: str = "linear"
    ) -> None:
        self.stages: list[CurriculumStage] = []
        self.current_stage: int = 0
        self.mastery_threshold = mastery_threshold
        self.schedule_type = schedule_type
        self._completed_tasks: int = 0

    def add_stage(
        self,
        name: str,
        difficulty: float,
        tasks: list[Any] | None = None,
        mastery_threshold: int | None = None,
    ) -> CurriculumStage:
        """Add a curriculum stage (backward-compatible)."""
        stage = CurriculumStage(
            name=name,
            difficulty=difficulty,
            tasks=tasks or [],
            mastery_threshold=mastery_threshold or self.mastery_threshold,
        )
        self.stages.append(stage)
        return stage

    def next_task(self) -> Any:
        """Get next task from current stage (backward-compatible)."""
        if not self.stages:
            return None

        idx = min(self.current_stage, len(self.stages) - 1)
        stage = self.stages[idx]

        if stage.tasks:
            return stage.tasks[min(stage.completed, len(stage.tasks) - 1)]
        return {"name": stage.name, "difficulty": stage.difficulty}

    def complete_task(self) -> None:
        """Mark current task as completed (backward-compatible)."""
        if not self.stages:
            return

        idx = min(self.current_stage, len(self.stages) - 1)
        stage = self.stages[idx]
        stage.completed += 1
        self._completed_tasks += 1

        # Auto-progress if mastery threshold met
        if stage.completed >= stage.mastery_threshold:
            self.current_stage = min(self.current_stage + 1, len(self.stages) - 1)

    def current_difficulty(self) -> float:
        """Return difficulty of current stage."""
        if not self.stages:
            return 0.0
        idx = min(self.current_stage, len(self.stages) - 1)
        return self.stages[idx].difficulty

    def mastery(self, stage_idx: int | None = None) -> float:
        """Return mastery level for a stage."""
        idx = stage_idx or self.current_stage
        idx = min(idx, len(self.stages) - 1)
        if not self.stages:
            return 0.0
        stage = self.stages[idx]
        return min(1.0, stage.completed / stage.mastery_threshold)

    def overall_progress(self) -> float:
        """Return overall curriculum progress."""
        if not self.stages:
            return 0.0
        return self.current_stage / len(self.stages)

    def generate_schedule(
        self,
        num_stages: int = 5,
        min_difficulty: float = 0.1,
        max_difficulty: float = 1.0,
    ) -> list[CurriculumStage]:
        """Auto-generate a difficulty schedule."""
        stages = []
        for i in range(num_stages):
            if self.schedule_type == "linear":
                difficulty = (
                    min_difficulty + (max_difficulty - min_difficulty) * i / num_stages
                )
            elif self.schedule_type == "exponential":
                difficulty = min_difficulty * (max_difficulty / min_difficulty) ** (
                    i / num_stages
                )
            else:
                difficulty = (
                    min_difficulty + (max_difficulty - min_difficulty) * i / num_stages
                )
            stage = CurriculumStage(name=f"stage_{i}", difficulty=round(difficulty, 4))
            stages.append(stage)
        self.stages = stages
        return stages

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "stages": len(self.stages),
            "current_stage": self.current_stage,
            "completed_tasks": self._completed_tasks,
            "current_difficulty": self.current_difficulty(),
            "overall_progress": round(self.overall_progress(), 4),
        }
