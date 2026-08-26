"""Runtime snapshot persistence layer."""


class RuntimeSnapshotStore:
    def __init__(self):
        self._snapshot = {}

    def save_runtime_snapshot(self, snapshot):
        self._snapshot = dict(snapshot)
        return self._snapshot

    def load_runtime_snapshot(self):
        return dict(self._snapshot)

    def clear(self):
        self._snapshot = {}
