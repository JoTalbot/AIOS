"""Prometheus-style Metrics Exporter for AIOS"""

from typing import Dict, Any


class MetricsExporter:
    """Exports AIOS metrics in Prometheus text format."""

    def __init__(self):
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}
        self._labels: Dict[str, Dict[str, str]] = {}

    def inc_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
        if labels:
            self._labels[key] = labels

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.gauges[key] = value
        if labels:
            self._labels[key] = labels

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        if labels:
            self._labels[key] = labels

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def export(self) -> str:
        lines = []
        # Counters
        seen_counter_names = set()
        for key, value in self.counters.items():
            name = key.split("{")[0]
            if name not in seen_counter_names:
                lines.append(f"# TYPE {name} counter")
                seen_counter_names.add(name)
            lines.append(f"{key} {value}")
        # Gauges
        seen_gauge_names = set()
        for key, value in self.gauges.items():
            name = key.split("{")[0]
            if name not in seen_gauge_names:
                lines.append(f"# TYPE {name} gauge")
                seen_gauge_names.add(name)
            lines.append(f"{key} {value}")
        # Histograms
        seen_hist_names = set()
        for key, values in self.histograms.items():
            name = key.split("{")[0]
            if name not in seen_hist_names:
                lines.append(f"# TYPE {name} summary")
                seen_hist_names.add(name)
            if values:
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values):.4f}")
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "counters": len(self.counters),
            "gauges": len(self.gauges),
            "histograms": len(self.histograms),
        }


metrics_exporter = MetricsExporter()
