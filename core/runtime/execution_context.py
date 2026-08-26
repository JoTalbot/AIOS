class ExecutionContext:
    def __init__(self, request_id=None, metadata=None):
        self.request_id = request_id
        self.metadata = metadata or {}
        self.events = []

    def add_event(self, event):
        self.events.append(event)
