"""metrics_exporter test."""
def test(): from aios_core.metrics_exporter import MetricsExporter; s = MetricsExporter().stats(); assert isinstance(s, dict)
