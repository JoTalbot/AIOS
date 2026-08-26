"""AIOS security audit log."""

from datetime import datetime


class AuditLog:
    def __init__(self):
        self.events = []

    def record(self, agent, action):
        self.events.append({
            "time": datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
        })

    def all(self):
        return self.events
