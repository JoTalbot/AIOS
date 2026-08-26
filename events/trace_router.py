class TraceRouter:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)
        return event

    def history(self):
        return list(self.events)
