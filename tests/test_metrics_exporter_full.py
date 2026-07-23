"""Metrics exporter full."""
from aios_core.metrics_exporter import MetricsExporter
def test(): s=MetricsExporter().stats(); assert isinstance(s,dict)
