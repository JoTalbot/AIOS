"""Production Telemetry & OTLP Metric Exporter Engine for AIOS Executive Layer.

Provides OpenTelemetry-compatible counters, gauges, histograms, metric rollups,
and Prometheus/OTLP metric formatting.
"""

import math
import time
from typing import Any, Dict, List, Optional

__all__ = ["MetricCounter", "MetricGauge", "MetricHistogram", "Telemetry"]


class MetricCounter:
    """Cumulative metric counter."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0.0

    def add(self, value: float = 1.0) -> None:
        self.value += value


class MetricGauge:
    """Instantaneous metric gauge."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0.0

    def set(self, value: float) -> None:
        self.value = value


class MetricHistogram:
    """Value distribution histogram with percentile aggregations."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.values: List[float] = []

    def observe(self, value: float) -> None:
        self.values.append(value)
        if len(self.values) > 5000:
            self.values = self.values[-5000:]

    def get_summary(self) -> Dict[str, float]:
        if not self.values:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }

        s_vals = sorted(self.values)
        count = len(s_vals)

        def percentile(p: float) -> float:
            idx = int(math.ceil((p / 100.0) * count)) - 1
            return s_vals[max(0, min(count - 1, idx))]

        return {
            "count": count,
            "min": round(s_vals[0], 4),
            "max": round(s_vals[-1], 4),
            "mean": round(sum(s_vals) / count, 4),
            "p50": round(percentile(50), 4),
            "p95": round(percentile(95), 4),
            "p99": round(percentile(99), 4),
        }


class Telemetry:
    """OpenTelemetry Metric Exporter and Collector for AIOS."""

    def __init__(self):
        self.counters: Dict[str, MetricCounter] = {}
        self.gauges: Dict[str, MetricGauge] = {}
        self.histograms: Dict[str, MetricHistogram] = {}
        self.recorded_events: List[Dict[str, Any]] = []

    def counter(self, name: str, description: str = "") -> MetricCounter:
        if name not in self.counters:
            self.counters[name] = MetricCounter(name, description)
        return self.counters[name]

    def create_counter(self, name: str, description: str = "") -> MetricCounter:
        """Create (or return) a counter.

        This explicit name is retained for compatibility with the original
        telemetry API; :meth:`counter` is the shorter OpenTelemetry-style API.
        """
        return self.counter(name, description)

    def increment_counter(self, name: str, value: float = 1.0) -> None:
        """Add *value* to a counter, creating it when necessary."""
        self.counter(name).add(value)

    def get_counter_value(self, name: str) -> float:
        """Return a counter value, or zero when it has not been recorded."""
        return self.counters.get(name, MetricCounter(name)).value

    def gauge(self, name: str, description: str = "") -> MetricGauge:
        if name not in self.gauges:
            self.gauges[name] = MetricGauge(name, description)
        return self.gauges[name]

    def create_gauge(self, name: str, description: str = "") -> MetricGauge:
        """Create (or return) a gauge."""
        return self.gauge(name, description)

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value, creating the gauge when necessary."""
        self.gauge(name).set(value)

    def get_gauge_value(self, name: str) -> float:
        """Return a gauge value, or zero when it has not been recorded."""
        return self.gauges.get(name, MetricGauge(name)).value

    def histogram(self, name: str, description: str = "") -> MetricHistogram:
        if name not in self.histograms:
            self.histograms[name] = MetricHistogram(name, description)
        return self.histograms[name]

    def create_histogram(self, name: str, description: str = "") -> MetricHistogram:
        """Create (or return) a histogram."""
        return self.histogram(name, description)

    def observe_histogram(self, name: str, value: float) -> None:
        """Record a histogram observation, creating it when necessary."""
        self.histogram(name).observe(value)

    def get_histogram_summary(self, name: str) -> Dict[str, float]:
        """Return summary statistics for a histogram, or an empty summary."""
        return self.histogram(name).get_summary()

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a generic metric observation."""
        hist = self.histogram(name)
        hist.observe(value)
        self.recorded_events.append(
            {"metric": name, "value": value, "tags": tags or {}, "ts": time.time()}
        )

    def export_prometheus_format(self) -> str:
        """Export current metric state in Prometheus exposition format."""
        lines = []
        for name, cnt in self.counters.items():
            lines.append(f"# HELP {name} {cnt.description}")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {cnt.value}")

        for name, g in self.gauges.items():
            lines.append(f"# HELP {name} {g.description}")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {g.value}")

        for name, h in self.histograms.items():
            summary = h.get_summary()
            lines.append(f"# HELP {name} {h.description}")
            lines.append(f"# TYPE {name} histogram")
            lines.append(f'{name}_count {summary["count"]}')
            lines.append(f"{name}_sum {sum(h.values)}")
            lines.append(f'{name}{{quantile="0.5"}} {summary["p50"]}')
            lines.append(f'{name}{{quantile="0.95"}} {summary["p95"]}')
            lines.append(f'{name}{{quantile="0.99"}} {summary["p99"]}')

        return "\n".join(lines)

    def export_prometheus(self) -> str:
        """Compatibility alias for :meth:`export_prometheus_format`."""
        return self.export_prometheus_format()

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return a serialisable snapshot of all collected metrics."""
        return {
            "counters": {name: counter.value for name, counter in self.counters.items()},
            "gauges": {name: gauge.value for name, gauge in self.gauges.items()},
            "histograms": {
                name: histogram.get_summary() for name, histogram in self.histograms.items()
            },
        }

    def export_json(self) -> Dict[str, Dict[str, Any]]:
        """Return the metric snapshot in a JSON-serialisable structure."""
        return self.get_all_metrics()

    def reset(self) -> None:
        """Remove all metric values and recorded metric events."""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.recorded_events.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "total_counters": len(self.counters),
            "total_gauges": len(self.gauges),
            "total_histograms": len(self.histograms),
            "recorded_events": len(self.recorded_events),
        }


telemetry = Telemetry()
