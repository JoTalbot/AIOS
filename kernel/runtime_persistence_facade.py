"""Runtime persistence facade.

Provides one runtime-facing API for events, recovery records and checkpoints.
"""


class RuntimePersistenceFacade:
    def __init__(self, adapter=None):
        self.adapter = adapter

    def attach(self, adapter):
        self.adapter = adapter

    def history(self):
        return self.adapter.history() if self.adapter and hasattr(self.adapter, "history") else []

    def last_recovery(self):
        return self.adapter.last_recovery() if self.adapter and hasattr(self.adapter, "last_recovery") else None

    def record(self, event):
        return self.adapter.record(event) if self.adapter and hasattr(self.adapter, "record") else None

    def save_checkpoint(self, checkpoint):
        if self.adapter and hasattr(self.adapter, "save_checkpoint"):
            return self.adapter.save_checkpoint(checkpoint)
        return None

    def load_checkpoint(self, task_id):
        if self.adapter and hasattr(self.adapter, "load_checkpoint"):
            return self.adapter.load_checkpoint(task_id)
        return None

    def delete_checkpoint(self, task_id):
        if self.adapter and hasattr(self.adapter, "delete_checkpoint"):
            return self.adapter.delete_checkpoint(task_id)
        return None

    def record_recovery(self, event):
        if self.adapter and hasattr(self.adapter, "record_recovery"):
            return self.adapter.record_recovery(event)
        return self.record(event)
