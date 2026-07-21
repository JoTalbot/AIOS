"""Production Telemetry & OTLP Metric Exporter Engine for AIOS Executive Layer.

Provides OpenTelemetry-compatible counters, gauges, histograms, metric rollups,
and Prometheus/OTLP metric formatting.
"""

import math
import time
from typing import Dict, List, Optional, Any


class MetricCounter:
    """Cumulative metric counter."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0.0

    def add(self, value: float = 1.0):
        self.value += value


class MetricGauge:
    """Instantaneous metric gauge."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.value = 0.0

    def set(self, value: float):
        self.value = value


class MetricHistogram:
    """Value distribution histogram with percentile aggregations."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.values: List[float] = []

    def observe(self, value: float):
        self.values.append(value)
        if len(self.values) > 5000:
            self.values = self.values[-5000:]

    def get_summary(self) -> Dict[str, float]:
        if not self.values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0}

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
            "p99": round(percentile(99), 4)
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

    def gauge(self, name: str, description: str = "") -> MetricGauge:
        if name not in self.gauges:
            self.gauges[name] = MetricGauge(name, description)
        return self.gauges[name]

    def histogram(self, name: str, description: str = "") -> MetricHistogram:
        if name not in self.histograms:
            self.histograms[name] = MetricHistogram(name, description)
        return self.histograms[name]

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a generic metric observation."""
        hist = self.histogram(name)
        hist.observe(value)
        self.recorded_events.append({"metric": name, "value": value, "tags": tags or {}, "ts": time.time()})

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
            lines.append(f"# TYPE {name} summary")
            lines.append(f'{name}_count {summary["count"]}')
            lines.append(f'{name}{{quantile="0.5"}} {summary["p50"]}')
            lines.append(f'{name}{{quantile="0.95"}} {summary["p95"]}')
            lines.append(f'{name}{{quantile="0.99"}} {summary["p99"]}')

        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_counters": len(self.counters),
            "total_gauges": len(self.gauges),
            "total_histograms": len(self.histograms),
            "recorded_events": len(self.recorded_events)
        }


telemetry = Telemetry()
