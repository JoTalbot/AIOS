"""Runtime persistence facade.

Provides a single runtime-facing API for persistence operations.
"""


class RuntimePersistenceFacade:
    def __init__(self, adapter=None):
        self.adapter = adapter

    def attach(self, adapter):
        self.adapter = adapter

    def history(self):
        if not self.adapter:
            return []
        return self.adapter.history()

    def last_recovery(self):
        if not self.adapter:
            return None
        return self.adapter.last_recovery()

    def record(self, event):
        if not self.adapter:
            return None
        return self.adapter.record(event)
