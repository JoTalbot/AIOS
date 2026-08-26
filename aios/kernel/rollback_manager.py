"""Rollback control for AIOS evolution lifecycle."""


class RollbackManager:
    def __init__(self):
        self.snapshots = []

    def snapshot(self, state):
        self.snapshots.append(state)
        return len(self.snapshots) - 1

    def rollback(self, index=-1):
        return self.snapshots[index]
