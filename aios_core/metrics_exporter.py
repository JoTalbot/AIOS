"""Prometheus-style Metrics Exporter for AIOS

Exports counters, gauges, and histograms in Prometheus exposition format.
Supports labeled metrics, histogram bucketing, summary quantiles,
metric metadata, reset/snapshot, and HTTP exposition endpoint helpers.
"""

import time
from collections.abc import Sequence
from typing import Any

__all__ = ["HistogramConfig", "MetricsExporter", "metrics_exporter"]


class HistogramConfig:
    """Configuration for histogram bucket boundaries."""

    __slots__ = ("buckets", "metric_name")

    def __init__(self, metric_name: str, buckets: Sequence[float] = None):
        self.metric_name = metric_name
        # Default Prometheus-style exponential buckets if not provided
        if buckets is None:
            self.buckets = [
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
            ]
        else:
            self.buckets = list(buckets)


class MetricsExporter:
    """Exports AIOS metrics in Prometheus text format.

    Features:
    - Counter, Gauge, and Histogram metric types
    - Label-based metric dimensionalities
    - Configurable histogram bucket boundaries
    - Summary quantile computation
    - Metric metadata (TYPE, HELP, UNIT)
    - Reset per-metric or global
    - Snapshot for point-in-time capture
    - Stats and metric registry management
    """

    def __init__(self) -> None:
        """Initialize MetricsExporter."""
        self.counters: dict[str, float] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list] = {}
        self._labels: dict[str, dict[str, str]] = {}
        self._metadata: dict[str, dict[str, str]] = {}  # name → {help, unit, type}
        self._hist_configs: dict[str, HistogramConfig] = {}
        self._creation_time: dict[str, float] = {}  # name → timestamp

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def set_metadata(
        self,
        name: str,
        help_text: str = "",
        unit: str = "",
        metric_type: str = "",
    ) -> None:
        """Set HELP, UNIT, and TYPE metadata for a metric."""
        self._metadata[name] = {
            "help": help_text,
            "unit": unit,
            "type": metric_type,
        }
        self._creation_time.setdefault(name, time.time())

    # ------------------------------------------------------------------
    # Counter
    # ------------------------------------------------------------------

    def inc_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
        if labels:
            self._labels[key] = labels
        self._creation_time.setdefault(name, time.time())

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Return current counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0.0)

    # ------------------------------------------------------------------
    # Gauge
    # ------------------------------------------------------------------

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric to *value*."""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        if labels:
            self._labels[key] = labels
        self._creation_time.setdefault(name, time.time())

    def inc_gauge(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a gauge by *value*."""
        key = self._make_key(name, labels)
        self.gauges[key] = self.gauges.get(key, 0) + value
        if labels:
            self._labels[key] = labels

    def dec_gauge(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Decrement a gauge by *value*."""
        self.inc_gauge(name, -value, labels)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Return current gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)

    # ------------------------------------------------------------------
    # Histogram
    # ------------------------------------------------------------------

    def configure_histogram(self, config: HistogramConfig) -> None:
        """Register histogram bucket configuration."""
        self._hist_configs[config.metric_name] = config

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Observe a value for histogram *name*."""
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        if labels:
            self._labels[key] = labels
        self._creation_time.setdefault(name, time.time())

    def get_histogram_stats(
        self, name: str, labels: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Compute histogram statistics: count, sum, buckets, min, max, mean."""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        if not values:
            return {
                "count": 0,
                "sum": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
                "buckets": {},
            }

        config = self._hist_configs.get(name)
        buckets = (
            config.buckets
            if config
            else [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        bucket_counts: dict[str, int] = {}
        for boundary in buckets:
            count = sum(1 for v in values if v <= boundary)
            bucket_counts[f"le={boundary}"] = count
        # +Inf bucket
        bucket_counts["le=+Inf"] = len(values)

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "buckets": bucket_counts,
        }

    # ------------------------------------------------------------------
    # Summary quantiles
    # ------------------------------------------------------------------

    def compute_summary(
        self,
        name: str,
        labels: dict[str, str] | None = None,
        quantiles: list[float] = [0.5, 0.9, 0.95, 0.99],
    ) -> dict[str, float]:
        """Compute summary quantiles for a histogram metric."""
        key = self._make_key(name, labels)
        values = sorted(self.histograms.get(key, []))
        if not values:
            return {f"quantile_{q}": 0.0 for q in quantiles}

        result: dict[str, float] = {}
        for q in quantiles:
            idx = max(0, min(len(values) - 1, int(q * len(values))))
            result[f"quantile_{q}"] = round(values[idx], 4)
        return result

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        """Generate metric key with optional label dimensions."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self) -> str:
        """Export all metrics in Prometheus exposition text format."""
        lines: list[str] = []

        # Counters
        seen_counter_names = set()
        for key, value in self.counters.items():
            name = key.split("{")[0]
            if name not in seen_counter_names:
                meta = self._metadata.get(name, {})
                if meta.get("help"):
                    lines.append(f"# HELP {name} {meta['help']}")
                lines.append(f"# TYPE {name} counter")
                seen_counter_names.add(name)
            created = self._creation_time.get(name, 0)
            lines.append(f"{key} {value}")
            if created:
                lines.append(f"{key}_created {created}")

        # Gauges
        seen_gauge_names = set()
        for key, value in self.gauges.items():
            name = key.split("{")[0]
            if name not in seen_gauge_names:
                meta = self._metadata.get(name, {})
                if meta.get("help"):
                    lines.append(f"# HELP {name} {meta['help']}")
                lines.append(f"# TYPE {name} gauge")
                seen_gauge_names.add(name)
            lines.append(f"{key} {value}")

        # Histograms with bucket boundaries
        seen_hist_names = set()
        for key, values in self.histograms.items():
            name = key.split("{")[0]
            config = self._hist_configs.get(name)
            buckets = (
                config.buckets
                if config
                else [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            )

            if name not in seen_hist_names:
                meta = self._metadata.get(name, {})
                if meta.get("help"):
                    lines.append(f"# HELP {name} {meta['help']}")
                lines.append(f"# TYPE {name} histogram")
                seen_hist_names.add(name)

            if values:
                # Bucket counts
                cumulative = 0
                for boundary in buckets:
                    count = sum(1 for v in values if v <= boundary)
                    cumulative += count
                    label_part = key.split("{")[1] if "{" in key else ""
                    if label_part:
                        label_part = label_part.rstrip("}") + f',le="{boundary}"'
                        lines.append(f"{name}{{{label_part}}} {cumulative}")
                    else:
                        lines.append(f'{name}_bucket{{le="{boundary}"}} {cumulative}')
                # +Inf
                lines.append(f'{name}_bucket{{le="+Inf"}} {len(values)}')
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values):.4f}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reset & Snapshot
    # ------------------------------------------------------------------

    def reset_metric(self, name: str) -> bool:
        """Reset all values for metric *name* (all label variants)."""
        keys_to_remove = []
        for key in list(self.counters.keys()):
            if key.split("{")[0] == name:
                keys_to_remove.append(("counter", key))
        for key in list(self.gauges.keys()):
            if key.split("{")[0] == name:
                keys_to_remove.append(("gauge", key))
        for key in list(self.histograms.keys()):
            if key.split("{")[0] == name:
                keys_to_remove.append(("histogram", key))

        for typ, key in keys_to_remove:
            if typ == "counter":
                self.counters.pop(key, None)
            elif typ == "gauge":
                self.gauges.pop(key, None)
            elif typ == "histogram":
                self.histograms.pop(key, None)
            self._labels.pop(key, None)

        return len(keys_to_remove) > 0

    def reset_all(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self._labels.clear()
        self._creation_time.clear()

    def snapshot(self) -> dict[str, Any]:
        """Capture a point-in-time snapshot of all metric values."""
        return {
            "timestamp": time.time(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self.histograms.items()
            },
            "labels": dict(self._labels),
            "metadata": dict(self._metadata),
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "counters": len(self.counters),
            "gauges": len(self.gauges),
            "histograms": len(self.histograms),
            "total_observations": sum(len(v) for v in self.histograms.values()),
            "configured_histograms": len(self._hist_configs),
            "metrics_with_metadata": len(self._metadata),
        }


# Global instance
metrics_exporter = MetricsExporter()
