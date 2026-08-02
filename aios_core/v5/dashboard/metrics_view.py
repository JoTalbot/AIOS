class MetricsView:
    """Runtime metrics view foundation."""

    def render(self, metrics=None):
        return metrics or {}
