"""
AIOS Snapshot Manager Layer v2.1.1

Manages system state snapshots.
"""


class SnapshotManager:
    def __init__(self):
        self.snapshots = []

    def create_snapshot(self, state: dict):
        snapshot = {"state": state, "status": "saved"}
        self.snapshots.append(snapshot)
        return snapshot

    def list_snapshots(self):
        return self.snapshots
