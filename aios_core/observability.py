"""Observability for AIOS v10.6.0.

Unified observability: counters, gauges, histograms, span-based traces,
structured logs, Prometheus export with labels, and OpenTelemetry-compatible
API.

Classes:
    MetricKind      — COUNTER / GAUGE / HISTOGRAM
    MetricEntry     — single metric with kind, labels, and values
    Span            — trace span with attributes and events
    LogEntry        — structured log record
    Observability   — full observability engine (metrics, traces, logs)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class MetricKind(StrEnum):
    """Metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


# ── Metric Entry ────────────────────────────────────────────────────────────


@dataclass
class MetricEntry:
    """Single metric with kind, labels, and accumulated values."""

    name: str
    kind: MetricKind
    labels: dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    values: list[float] = field(default_factory=list)  # for histograms
    unit: str = ""
    description: str = ""

    def increment(self, amount: float = 1.0) -> None:
        """Increment counter or gauge."""
        self.value += amount

    def set_value(self, value: float) -> None:
        """Set gauge value."""
        self.value = value

    def observe(self, value: float) -> None:
        """Record histogram observation."""
        self.values.append(value)
        self.value = sum(self.values) / len(self.values) if self.values else 0.0

    def key(self) -> str:
        """Generate unique metric key from name + labels."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(self.labels.items()))
        return f"{self.name}{label_str}"


# ── Span ────────────────────────────────────────────────────────────────────


@dataclass
class SpanEvent:
    """Event within a trace span."""

    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Trace span with start/end, attributes, and events."""

    trace_id: str
    span_id: str = ""
    name: str = ""
    parent_span_id: str | None = None
    start_time: float = 0.0
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    status: str = "ok"  # ok, error

    def duration_ms(self) -> float:
        """Return span duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span."""
        self.events.append(SpanEvent(name=name, attributes=attributes or {}))

    def end(self) -> None:
        """End the span."""
        self.end_time = time.time()


# ── Log Entry ───────────────────────────────────────────────────────────────


@dataclass
class LogEntry:
    """Structured log record."""

    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    attributes: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None


# ── Observability ───────────────────────────────────────────────────────────


class Observability:
    """Full observability engine: metrics, traces, logs.

    Features:
    - Counter, gauge, and histogram metrics with labels
    - Span-based traces with nested spans and events
    - Structured logs with trace correlation
    - Prometheus export format
    - Metric aggregation (sum, avg, min, max)
    """

    def __init__(self) -> None:
        self.metrics: dict[str, MetricEntry] = {}
        self.traces: dict[str, list[Span]] = {}  # trace_id → spans
        self.logs: list[LogEntry] = []
        self._span_counter: int = 0

    # ── Metrics ──────────────────────────────────────────────────

    def register_metric(
        self,
        name: str,
        kind: MetricKind,
        unit: str = "",
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> MetricEntry:
        """Register a metric."""
        entry = MetricEntry(
            name=name,
            kind=kind,
            unit=unit,
            description=description,
            labels=labels or {},
        )
        self.metrics[entry.key()] = entry
        return entry

    def record_metric(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a metric value (backward-compatible)."""
        label_str = labels or {}
        entry = MetricEntry(name=name, kind=MetricKind.GAUGE, labels=label_str)
        entry.set_value(value)
        self.metrics[entry.key()] = entry

    def increment(
        self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        key = MetricEntry(name=name, kind=MetricKind.COUNTER, labels=labels or {}).key()
        if key not in self.metrics:
            self.metrics[key] = MetricEntry(
                name=name, kind=MetricKind.COUNTER, labels=labels or {}
            )
        self.metrics[key].increment(amount)

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record histogram observation."""
        key = MetricEntry(
            name=name, kind=MetricKind.HISTOGRAM, labels=labels or {}
        ).key()
        if key not in self.metrics:
            self.metrics[key] = MetricEntry(
                name=name, kind=MetricKind.HISTOGRAM, labels=labels or {}
            )
        self.metrics[key].observe(value)

    def get_metric(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get metric value."""
        key = MetricEntry(name=name, kind=MetricKind.GAUGE, labels=labels or {}).key()
        entry = self.metrics.get(key)
        return entry.value if entry else 0.0

    def get_metric_entry(
        self, name: str, labels: dict[str, str] | None = None
    ) -> MetricEntry | None:
        """Get full metric entry."""
        key = MetricEntry(name=name, kind=MetricKind.GAUGE, labels=labels or {}).key()
        return self.metrics.get(key)

    def get_all_metrics(self) -> dict[str, MetricEntry]:
        """Return all metric entries."""
        return self.metrics.copy()

    # ── Traces ──────────────────────────────────────────────────

    def start_trace(self, name: str, attributes: dict[str, str] | None = None) -> str:
        """Start a new trace. Returns trace_id."""
        trace_id = f"trace_{self._span_counter}"
        self._span_counter += 1

        root_span = Span(
            trace_id=trace_id,
            span_id=f"span_{self._span_counter}",
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        self._span_counter += 1
        self.traces[trace_id] = [root_span]
        return trace_id

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> str:
        """Start a nested span within a trace."""
        spans = self.traces.get(trace_id, [])
        span_id = f"span_{self._span_counter}"
        self._span_counter += 1

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            name=name,
            parent_span_id=parent_span_id,
            start_time=time.time(),
            attributes=attributes or {},
        )
        spans.append(span)
        self.traces[trace_id] = spans
        return span_id

    def end_trace(self, trace_id: str) -> None:
        """End all spans in a trace."""
        spans = self.traces.get(trace_id, [])
        for span in spans:
            if span.end_time is None:
                span.end()

    def end_span(self, trace_id: str, span_id: str) -> None:
        """End a specific span."""
        spans = self.traces.get(trace_id, [])
        for span in spans:
            if span.span_id == span_id and span.end_time is None:
                span.end()
                break

    def get_trace(self, trace_id: str) -> list[Span]:
        """Return all spans in a trace."""
        return self.traces.get(trace_id, [])

    def get_trace_duration(self, trace_id: str) -> float:
        """Return total trace duration in ms."""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return 0.0
        root = spans[0]
        return root.duration_ms()

    # ── Logs ────────────────────────────────────────────────────

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """Add a structured log entry."""
        self.logs.append(LogEntry(level=level, message=message, attributes=kwargs))

    def log_with_trace(
        self,
        level: str,
        message: str,
        trace_id: str,
        span_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Add a log entry correlated with a trace."""
        self.logs.append(
            LogEntry(
                level=level,
                message=message,
                trace_id=trace_id,
                span_id=span_id,
                attributes=kwargs,
            )
        )

    def get_logs(
        self, level: str | None = None, trace_id: str | None = None, limit: int = 100
    ) -> list[LogEntry]:
        """Query logs by level or trace."""
        result = self.logs
        if level:
            result = [l for l in result if l.level == level]
        if trace_id:
            result = [l for l in result if l.trace_id == trace_id]
        return result[-limit:]

    # ── Prometheus Export ────────────────────────────────────────

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus exposition format."""
        lines = []
        for entry in self.metrics.values():
            metric_name = entry.name.replace(".", "_").replace("-", "_")
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(entry.labels.items()))

            # HELP line
            if entry.description:
                lines.append(f"# HELP {metric_name} {entry.description}")

            # Type line
            lines.append(f"# TYPE {metric_name} {entry.kind.value}")

            # Value line
            if label_str:
                lines.append(f"{metric_name}{{{label_str}}} {entry.value}")
            else:
                lines.append(f"{metric_name} {entry.value}")

            # Histogram buckets
            if entry.kind == MetricKind.HISTOGRAM and entry.values:
                lines.append(
                    f"# Histogram {metric_name}: count={len(entry.values)}, sum={sum(entry.values)}, avg={entry.value}"
                )

        return "\n".join(lines)

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "metrics": len(self.metrics),
            "traces": len(self.traces),
            "logs": len(self.logs),
            "span_count": sum(len(spans) for spans in self.traces.values()),
        }


observability = Observability()
