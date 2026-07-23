"""metrics_exporter test."""
from aios_core.metrics_exporter import MetricsExporter
def test_init(): s = MetricsExporter().stats(); assert isinstance(s, dict)
