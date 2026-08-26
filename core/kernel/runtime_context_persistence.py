"""Runtime persistence wiring layer.

Connects RuntimeContext with the persistence facade.
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
        if not self.facade:
            return []
        return self.facade.history()

    def last_recovery(self):
        if not self.facade:
            return None
        return self.facade.last_recovery()
