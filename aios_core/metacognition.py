"""Meta-Cognition for AIOS v10.8.0.

Thinking about thinking with self-monitoring,
confidence calibration, knowledge gap detection,
reasoning reflection, cognitive load estimation,
strategy selection, and self-assessment.

Classes:
    MonitoringEvent — recorded monitoring observation
    KnowledgeGap    — identified knowledge gap
    MetaCognition   — full metacognitive reasoning engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MonitoringEvent:
    """Recorded monitoring observation."""

    task: str
    confidence: float
    actual_performance: float = 0.0
    strategy: str = ""
    cognitive_load: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class KnowledgeGap:
    """Identified knowledge gap."""

    area: str
    severity: float = 0.5  # 0..1
    description: str = ""
    discovered_at: float = field(default_factory=time.time)
    resolved: bool = False


class MetaCognition:
    """Full metacognitive reasoning engine.

    Features:
    - Self-monitoring (confidence vs actual performance tracking)
    - Confidence calibration (adjust overconfident/underconfident estimates)
    - Knowledge gap detection
    - Reasoning reflection (analyze past decisions)
    - Cognitive load estimation
    - Strategy selection based on self-knowledge
    - Self-assessment with calibration metrics
    """

    def __init__(self) -> None:
        self.knowledge_about_knowledge: dict[str, float] = {}
        self.confidence_estimates: dict[str, float] = {}
        self.monitoring: list[MonitoringEvent] = []
        self.knowledge_gaps: list[KnowledgeGap] = []
        self._calibration_data: list[tuple[float, float]] = []  # (predicted, actual)
        self._strategy_history: dict[str, list[float]] = {}

    # ── Self-Monitoring ─────────────────────────────────────────────

    def monitor_reasoning(
        self,
        task: str,
        confidence: float,
        strategy: str = "",
        cognitive_load: float = 0.0,
    ) -> MonitoringEvent:
        """Monitor a reasoning task with confidence estimate."""
        event = MonitoringEvent(
            task=task,
            confidence=confidence,
            strategy=strategy,
            cognitive_load=cognitive_load,
        )
        self.monitoring.append(event)
        self.confidence_estimates[task] = confidence
        return event

    def record_actual_performance(self, task: str, actual_performance: float) -> None:
        """Record actual performance for calibration."""
        predicted = self.confidence_estimates.get(task, 0.5)
        self._calibration_data.append((predicted, actual_performance))

        # Update the corresponding monitoring event
        for event in reversed(self.monitoring):
            if event.task == task and event.actual_performance == 0.0:
                event.actual_performance = actual_performance
                break

    # ── Confidence Calibration ──────────────────────────────────────

    def calibration_error(self) -> float:
        """Compute mean calibration error (ECE)."""
        if not self._calibration_data:
            return 0.0
        errors = [abs(p - a) for p, a in self._calibration_data]
        return sum(errors) / len(errors)

    def is_overconfident(self) -> bool:
        """Check if the system is systematically overconfident."""
        if not self._calibration_data:
            return False
        avg_predicted = sum(p for p, a in self._calibration_data) / len(
            self._calibration_data
        )
        avg_actual = sum(a for p, a in self._calibration_data) / len(
            self._calibration_data
        )
        return avg_predicted > avg_actual + 0.1

    def is_underconfident(self) -> bool:
        """Check if the system is systematically underconfident."""
        if not self._calibration_data:
            return False
        avg_predicted = sum(p for p, a in self._calibration_data) / len(
            self._calibration_data
        )
        avg_actual = sum(a for p, a in self._calibration_data) / len(
            self._calibration_data
        )
        return avg_actual > avg_predicted + 0.1

    def calibrate_confidence(self, task: str) -> float:
        """Calibrate confidence for a task based on past performance."""
        if not self._calibration_data:
            return self.confidence_estimates.get(task, 0.5)

        base_confidence = self.confidence_estimates.get(task, 0.5)
        avg_error = self.calibration_error()

        if self.is_overconfident():
            calibrated = base_confidence - avg_error * 0.5
        elif self.is_underconfident():
            calibrated = base_confidence + avg_error * 0.5
        else:
            calibrated = base_confidence

        return max(0.0, min(1.0, calibrated))

    # ── Self-Assessment ──────────────────────────────────────────────

    def self_assess(self, performance: float) -> dict[str, Any]:
        """Assess metacognitive state based on performance."""
        awareness = performance > 0.7
        calibration = abs(performance - 0.75) < 0.2

        # Add to calibration data
        confidence_avg = (
            (sum(self.confidence_estimates.values()) / len(self.confidence_estimates))
            if self.confidence_estimates
            else 0.5
        )
        self._calibration_data.append((confidence_avg, performance))

        return {
            "awareness": awareness,
            "calibration": calibration,
            "confidence_error": round(self.calibration_error(), 4),
            "overconfident": self.is_overconfident(),
            "underconfident": self.is_underconfident(),
            "knowledge_gaps": len([g for g in self.knowledge_gaps if not g.resolved]),
        }

    # ── Knowledge Gap Detection ─────────────────────────────────────

    def detect_knowledge_gap(self, area: str, confidence: float = 0.3) -> KnowledgeGap:
        """Detect a knowledge gap based on low confidence."""
        severity = 1.0 - confidence
        gap = KnowledgeGap(
            area=area,
            severity=severity,
            description=f"Low confidence ({confidence}) in {area}",
        )
        self.knowledge_gaps.append(gap)
        self.knowledge_about_knowledge[area] = confidence
        return gap

    def resolve_knowledge_gap(self, area: str) -> bool:
        """Mark a knowledge gap as resolved."""
        for gap in self.knowledge_gaps:
            if gap.area == area and not gap.resolved:
                gap.resolved = True
                return True
        return False

    def get_unresolved_gaps(self) -> list[KnowledgeGap]:
        """Return all unresolved knowledge gaps."""
        return [g for g in self.knowledge_gaps if not g.resolved]

    # ── Strategy Selection ──────────────────────────────────────────

    def select_strategy(self, task: str, available_strategies: list[str]) -> str:
        """Select best strategy based on metacognitive assessment."""
        confidence = self.confidence_estimates.get(task, 0.5)

        if confidence > 0.8:
            # High confidence: use fast strategy
            return available_strategies[0] if available_strategies else "direct"
        elif confidence > 0.5:
            # Medium confidence: use careful strategy
            return (
                available_strategies[-1] if len(available_strategies) > 1 else "careful"
            )
        else:
            # Low confidence: seek external help or explore
            return "explore" if "explore" in available_strategies else "ask_for_help"

    # ── Reasoning Reflection ────────────────────────────────────────

    def reflect(self) -> dict[str, Any]:
        """Reflect on recent monitoring data."""
        recent = (
            self.monitoring[-10:] if len(self.monitoring) >= 10 else self.monitoring
        )
        avg_confidence = (
            (sum(e.confidence for e in recent) / len(recent)) if recent else 0.5
        )
        avg_performance = (
            (sum(e.actual_performance for e in recent) / len(recent)) if recent else 0.0
        )
        avg_load = (
            (sum(e.cognitive_load for e in recent) / len(recent)) if recent else 0.0
        )

        return {
            "recent_events": len(recent),
            "avg_confidence": round(avg_confidence, 4),
            "avg_performance": round(avg_performance, 4),
            "avg_cognitive_load": round(avg_load, 4),
            "calibration_error": round(self.calibration_error(), 4),
            "knowledge_gaps_unresolved": len(self.get_unresolved_gaps()),
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "monitoring_events": len(self.monitoring),
            "confidence_estimates": len(self.confidence_estimates),
            "knowledge_areas": len(self.knowledge_about_knowledge),
            "knowledge_gaps": len(self.knowledge_gaps),
            "gaps_resolved": sum(1 for g in self.knowledge_gaps if g.resolved),
            "calibration_error": round(self.calibration_error(), 4),
            "overconfident": self.is_overconfident(),
        }
