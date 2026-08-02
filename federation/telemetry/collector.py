class TelemetryCollector:
    """Federation telemetry collection foundation."""

    def __init__(self):
        self.records = []

    def collect(self, event):
        self.records.append(event)

    def all(self):
        return self.records
