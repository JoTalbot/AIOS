"""Graceful shutdown foundation."""

class ShutdownManager:
    def __init__(self):
        self.closed = False

    def shutdown(self):
        self.closed = True
        return {"status": "stopped"}
