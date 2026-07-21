"""Prometheus-style Metrics Exporter for AIOS"""

from typing import Dict, Any


class MetricsExporter:
    """Exports AIOS metrics in Prometheus text format."""

    def __init__(self):
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}

    def inc_counter(self, name: str, value: float = 1.0):
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float):
        self.gauges[name] = value

    def export(self) -> str:
        lines = []
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "counters": len(self.counters),
            "gauges": len(self.gauges)
        }


metrics_exporter = MetricsExporter()