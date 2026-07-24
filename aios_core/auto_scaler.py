"""Auto-Scaler for AIOS v10.5.0.

HPA-like auto-scaler with cooldown periods, stabilization windows,
multiple metric thresholds, prediction, scaling events history,
and configurable policies.

Classes:
    ScalingDirection — UP / DOWN / NONE
    ScalingPolicy    — single threshold rule for a metric
    ScalingEvent     — recorded scaling decision with reasons
    AutoScaler       — full scaler with policies, cooldown, prediction
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class ScalingDirection(str, Enum):
    """Scaling direction."""
    UP = "up"
    DOWN = "down"
    NONE = "none"


# ── Scaling Policy ───────────────────────────────────────────────────────────

@dataclass
class ScalingPolicy:
    """Single threshold rule for a metric."""
    name: str
    metric_name: str  # cpu_usage, queue_size, error_rate, latency
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 30.0
    scale_up_step: int = 2  # replicas to add
    scale_down_step: int = 1  # replicas to remove


# ── Scaling Event ────────────────────────────────────────────────────────────

@dataclass
class ScalingEvent:
    """Recorded scaling decision with reasons."""
    direction: ScalingDirection
    replicas_before: int
    replicas_after: int
    reason: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ── Auto-Scaler ──────────────────────────────────────────────────────────────

class AutoScaler:
    """Full HPA-like auto-scaler with policies, cooldown, prediction.

    Features:
    - Multiple metric threshold policies
    - Cooldown period between scaling decisions
    - Stabilization window (delay before scaling down)
    - Scaling event history with reasons
    - Current metrics tracking
    - Predictive scaling based on trend
    """

    def __init__(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        cooldown_seconds: float = 60.0,
        stabilization_window: float = 300.0,
    ) -> None:
        """Initialize AutoScaler.

        Args:
            min_replicas: Minimum number of replicas.
            max_replicas: Maximum number of replicas.
            cooldown_seconds: Minimum time between scaling decisions.
            stabilization_window: Delay before scaling down after scaling up.
        """
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.current_replicas = min_replicas
        self.cooldown_seconds = cooldown_seconds
        self.stabilization_window = stabilization_window

        self.policies: list[ScalingPolicy] = []
        self.events: list[ScalingEvent] = []
        self._current_metrics: dict[str, float] = {}
        self._last_scale_up_time: float = 0.0
        self._last_scale_down_time: float = 0.0

    # ── Policy Management ────────────────────────────────────────

    def add_policy(self, policy: ScalingPolicy) -> None:
        """Add a scaling policy."""
        self.policies.append(policy)

    def remove_policy(self, name: str) -> None:
        """Remove a policy by name."""
        self.policies = [p for p in self.policies if p.name != name]

    # ── Metrics ──────────────────────────────────────────────────

    def set_metrics(self, metrics: dict[str, float]) -> None:
        """Set current metrics values."""
        self._current_metrics = metrics

    def get_metric(self, name: str) -> float:
        """Get a specific metric value."""
        return self._current_metrics.get(name, 0.0)

    # ── Scaling Decision ─────────────────────────────────────────

    def evaluate(self) -> ScalingDirection:
        """Evaluate all policies and decide scaling direction.

        Checks cooldown and stabilization window before deciding.
        Returns the recommended direction.
        """
        now = time.time()

        # ── Check cooldown ──
        last_event_time = max(self._last_scale_up_time, self._last_scale_down_time)
        if last_event_time and now - last_event_time < self.cooldown_seconds:
            return ScalingDirection.NONE

        # ── Check stabilization window ──
        # Don't scale down if we recently scaled up
        if self._last_scale_up_time and now - self._last_scale_up_time < self.stabilization_window:
            # Only allow scale UP during stabilization
            pass

        # ── Evaluate policies ──
        should_scale_up = False
        should_scale_down = True  # assume down unless any policy says up
        up_reasons: list[str] = []
        down_reasons: list[str] = []

        for policy in self.policies:
            value = self._current_metrics.get(policy.metric_name, 0.0)
            if value > policy.scale_up_threshold:
                should_scale_up = True
                should_scale_down = False
                up_reasons.append(f"{policy.metric_name}={value} > {policy.scale_up_threshold}")
            elif value < policy.scale_down_threshold:
                down_reasons.append(f"{policy.metric_name}={value} < {policy.scale_down_threshold}")
            else:
                should_scale_down = False  # at least one metric in normal range

        # ── Stabilization override ──
        if self._last_scale_up_time and now - self._last_scale_up_time < self.stabilization_window:
            should_scale_down = False

        if should_scale_up:
            return ScalingDirection.UP
        if should_scale_down and down_reasons:
            return ScalingDirection.DOWN
        return ScalingDirection.NONE

    def scale(self, metrics: dict[str, float] | None = None) -> int:
        """Evaluate and apply scaling decision.

        Backward-compatible: also accepts cpu_usage and queue_size directly.
        """
        if metrics:
            self.set_metrics(metrics)

        # ── Backward-compatible shortcut ──
        if not self.policies:
            cpu = self._current_metrics.get("cpu_usage", 0.0)
            queue = self._current_metrics.get("queue_size", 0.0)
            if cpu > 80 or queue > 50:
                self.current_replicas = min(self.current_replicas + 1, self.max_replicas)
            elif cpu < 30 and queue < 5:
                self.current_replicas = max(self.current_replicas - 1, self.min_replicas)
            return self.current_replicas

        direction = self.evaluate()

        if direction == ScalingDirection.UP:
            # Apply scale up from the most aggressive policy
            step = max(p.scale_up_step for p in self.policies)
            new_replicas = min(self.current_replicas + step, self.max_replicas)
            event = ScalingEvent(
                direction=ScalingDirection.UP,
                replicas_before=self.current_replicas,
                replicas_after=new_replicas,
                reason=f"Metrics exceeded thresholds",
                metrics=self._current_metrics.copy(),
            )
            self.events.append(event)
            self.current_replicas = new_replicas
            self._last_scale_up_time = time.time()

        elif direction == ScalingDirection.DOWN:
            step = max(p.scale_down_step for p in self.policies)
            new_replicas = max(self.current_replicas - step, self.min_replicas)
            event = ScalingEvent(
                direction=ScalingDirection.DOWN,
                replicas_before=self.current_replicas,
                replicas_after=new_replicas,
                reason=f"Metrics below thresholds",
                metrics=self._current_metrics.copy(),
            )
            self.events.append(event)
            self.current_replicas = new_replicas
            self._last_scale_down_time = time.time()

        return self.current_replicas

    # ── Prediction ───────────────────────────────────────────────

    def predict_scale(self, projected_metrics: dict[str, float]) -> ScalingDirection:
        """Predict scaling direction based on projected future metrics."""
        self.set_metrics(projected_metrics)
        return self.evaluate()

    # ── History ──────────────────────────────────────────────────

    def get_events(self, direction: ScalingDirection | None = None, limit: int = 50) -> list[ScalingEvent]:
        """Return scaling events, optionally filtered by direction."""
        events = self.events
        if direction:
            events = [e for e in events if e.direction == direction]
        return events[-limit:]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "current": self.current_replicas,
            "min": self.min_replicas,
            "max": self.max_replicas,
            "policies": len(self.policies),
            "events": len(self.events),
            "cooldown_seconds": self.cooldown_seconds,
            "stabilization_window": self.stabilization_window,
        }


auto_scaler = AutoScaler()
