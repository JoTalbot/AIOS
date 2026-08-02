class MetricsCollector:
    """AIOS metrics collection foundation."""

    def collect(self, source):
        return {
            "source": source,
            "metrics": True
        }
