"""Experiment Tracking for AIOS v10.6.0.

Full ML experiment lifecycle: parameters, metrics, tags, artifacts,
comparisons, best experiment selection, nested runs, and status tracking.

Classes:
    ExperimentStatus — RUNNING / COMPLETED / FAILED / STOPPED
    Experiment       — full experiment definition
    ExperimentTracker — enhanced tracker with comparisons and selection
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class ExperimentStatus(str, Enum):
    """Experiment lifecycle status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


# ── Experiment ───────────────────────────────────────────────────────────────

@dataclass
class Experiment:
    """Full experiment definition."""
    id: str = ""
    name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)  # name → path/description
    status: ExperimentStatus = ExperimentStatus.RUNNING
    parent_id: Optional[str] = None  # for nested runs
    created_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def duration(self) -> float:
        """Return experiment duration."""
        if self.ended_at and self.created_at:
            return self.ended_at - self.created_at
        return time.time() - self.created_at

    def is_completed(self) -> bool:
        """Check if experiment is finished."""
        return self.status in (ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.STOPPED)


# ── Experiment Tracker ──────────────────────────────────────────────────────

class ExperimentTracker:
    """Enhanced experiment tracker with comparisons and selection.

    Features:
    - Full experiment lifecycle (start → log → end)
    - Tags for categorization and filtering
    - Artifacts tracking
    - Nested runs (parent_id)
    - Metric comparison across experiments
    - Best experiment selection by metric
    - Experiment listing and filtering
    """

    def __init__(self) -> None:
        self.experiments: dict[str, Experiment] = {}

    # ── Lifecycle ──────────────────────────────────────────────

    def start_experiment(self, name: str, params: dict[str, Any],
                         tags: list[str] | None = None,
                         parent_id: str | None = None) -> Experiment:
        """Start a new experiment."""
        exp = Experiment(name=name, params=params, tags=tags or [], parent_id=parent_id)
        self.experiments[exp.id] = exp
        return exp

    def log_metric(self, exp_id: str, metric: str, value: float) -> None:
        """Log a metric for an experiment."""
        exp = self._get(exp_id)
        exp.metrics[metric] = value

    def log_metrics(self, exp_id: str, metrics: dict[str, float]) -> None:
        """Log multiple metrics at once."""
        exp = self._get(exp_id)
        exp.metrics.update(metrics)

    def log_artifact(self, exp_id: str, name: str, path: str) -> None:
        """Log an artifact for an experiment."""
        exp = self._get(exp_id)
        exp.artifacts[name] = path

    def add_tag(self, exp_id: str, tag: str) -> None:
        """Add a tag to an experiment."""
        exp = self._get(exp_id)
        if tag not in exp.tags:
            exp.tags.append(tag)

    def add_note(self, exp_id: str, note: str) -> None:
        """Add a note to an experiment."""
        exp = self._get(exp_id)
        exp.notes = note

    def end_experiment(self, exp_id: str, status: ExperimentStatus = ExperimentStatus.COMPLETED) -> None:
        """End an experiment."""
        exp = self._get(exp_id)
        exp.status = status
        exp.ended_at = time.time()

    def stop_experiment(self, exp_id: str) -> None:
        """Stop an experiment (user-initiated)."""
        self.end_experiment(exp_id, status=ExperimentStatus.STOPPED)

    def fail_experiment(self, exp_id: str) -> None:
        """Mark experiment as failed."""
        self.end_experiment(exp_id, status=ExperimentStatus.FAILED)

    # ── Comparison ─────────────────────────────────────────────

    def compare(self, exp_ids: list[str], metric: str | None = None) -> dict[str, dict[str, float]]:
        """Compare metrics across experiments."""
        result = {}
        for exp_id in exp_ids:
            exp = self.experiments.get(exp_id)
            if exp is None:
                continue
            if metric:
                result[exp_id] = {metric: exp.metrics.get(metric, 0.0)}
            else:
                result[exp_id] = exp.metrics.copy()
        return result

    def best_experiment(self, metric: str, direction: str = "max") -> Experiment | None:
        """Find the best experiment by a specific metric.

        direction: 'max' → highest metric, 'min' → lowest metric.
        """
        candidates = [e for e in self.experiments.values() if metric in e.metrics and e.is_completed()]
        if not candidates:
            return None
        if direction == "max":
            return max(candidates, key=lambda e: e.metrics[metric])
        return min(candidates, key=lambda e: e.metrics[metric])

    # ── Filtering ──────────────────────────────────────────────

    def list_experiments(self, status: ExperimentStatus | None = None,
                         tag: str | None = None) -> list[Experiment]:
        """List experiments with optional filtering."""
        result = list(self.experiments.values())
        if status:
            result = [e for e in result if e.status == status]
        if tag:
            result = [e for e in result if tag in e.tags]
        return result

    def get_experiment(self, exp_id: str) -> Experiment:
        """Return experiment by ID."""
        return self._get(exp_id)

    def get_nested_runs(self, parent_id: str) -> list[Experiment]:
        """Return all nested runs for a parent experiment."""
        return [e for e in self.experiments.values() if e.parent_id == parent_id]

    # ── Stats ──────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_status = {}
        for exp in self.experiments.values():
            s = exp.status.value
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "experiments": len(self.experiments),
            "by_status": by_status,
            "completed": sum(1 for e in self.experiments.values() if e.status == ExperimentStatus.COMPLETED),
        }

    # ── Internal ───────────────────────────────────────────────

    def _get(self, exp_id: str) -> Experiment:
        """Get experiment or raise KeyError."""
        if exp_id not in self.experiments:
            raise KeyError(f"Experiment '{exp_id}' not found")
        return self.experiments[exp_id]
