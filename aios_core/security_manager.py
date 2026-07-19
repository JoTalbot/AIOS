"""
AIOS Security Manager Layer v2.1.1

Manages security rules and security events.
"""


class SecurityManager:
    def __init__(self):
        self.events = []

    def register_event(self, event: dict):
        self.events.append(event)
        return event

    def history(self):
        return self.events
