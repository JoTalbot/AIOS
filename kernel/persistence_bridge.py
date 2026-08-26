"""Bridge persistence hooks with runtime event emitters."""


class PersistenceBridge:
    """Connect lifecycle event streams to persistence hooks."""

    def __init__(self, hooks=None):
        self.hooks = hooks

    def attach(self, emitter):
        if emitter is None or self.hooks is None:
            return emitter
        emitter.persistence_hooks = self.hooks
        return emitter
