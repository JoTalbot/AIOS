class AlertManager:
    """Production alert management foundation."""

    def __init__(self):
        self.alerts = []

    def trigger(self, alert):
        self.alerts.append(alert)

    def list(self):
        return self.alerts
