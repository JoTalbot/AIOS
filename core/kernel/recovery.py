"""Kernel state recovery from persisted events."""


class KernelRecovery:
    def __init__(self, event_store):
        self.event_store = event_store

    def replay(self):
        return self.event_store.replay()

    def restore_status(self, state):
        for event in self.replay():
            if event.name == "kernel.started":
                state.status = "RUNNING"
            elif event.name == "kernel.stopped":
                state.status = "STOPPED"

        return state
