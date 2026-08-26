"""Persistent event storage foundation."""


class EventStore:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

    def replay(self):
        return list(self.events)
