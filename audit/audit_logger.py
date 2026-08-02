class AuditLogger:
    """AIOS audit logging foundation."""

    def __init__(self):
        self.logs = []

    def record(self, event):
        self.logs.append(event)

    def all(self):
        return self.logs
