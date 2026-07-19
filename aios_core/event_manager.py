"""AIOS Event Processing Layer v2.1.1"""

class EventManager:
    def __init__(self):
        self.events = []

    def add(self, event):
        self.events.append(event)
