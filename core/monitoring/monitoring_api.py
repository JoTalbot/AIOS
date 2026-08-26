"""Monitoring API adapter for AIOS.

Provides a lightweight interface between monitoring state and external consumers.
"""


class MonitoringAPI:
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def get_status(self):
        snapshot = self.dashboard.latest()
        return snapshot

    def get_history(self):
        return self.dashboard.history()

    def metrics(self):
        snapshot = self.dashboard.latest()
        return {
            "status": snapshot,
            "available": snapshot is not None,
        }
