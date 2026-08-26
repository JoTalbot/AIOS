"""AIOS v20 Rollback Manager."""


class RollbackManager:
    def __init__(self):
        self.snapshots = []

    def create_snapshot(self, state):
        self.snapshots.append(state)
        return len(self.snapshots) - 1

    def restore(self, snapshot_id):
        return self.snapshots[snapshot_id]
