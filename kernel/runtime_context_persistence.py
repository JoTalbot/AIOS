"""Runtime persistence wiring layer.

Connects RuntimeContext with the persistence facade and checkpoint contract.
"""


class RuntimeContextPersistence:
    def __init__(self, context, facade=None):
        self.context = context
        self.facade = facade

    def attach(self, facade):
        self.facade = facade
        if self.context is not None:
            self.context.persistence = facade
        return facade

    def history(self):
        return self.facade.history() if self.facade else []

    def last_recovery(self):
        return self.facade.last_recovery() if self.facade else None

    def record_recovery(self, decision):
        if not self.facade:
            return None
        return self.facade.record_recovery({
            "type": "recovery.decision",
            "decision": decision,
        })

    def save_checkpoint(self, checkpoint):
        return self.facade.save_checkpoint(checkpoint) if self.facade else None

    def load_checkpoint(self, task_id):
        return self.facade.load_checkpoint(task_id) if self.facade else None

    def delete_checkpoint(self, task_id):
        return self.facade.delete_checkpoint(task_id) if self.facade else None
