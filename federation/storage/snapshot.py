class SnapshotManager:
    """Federation state snapshot foundation."""

    def create(self, state):
        return {
            "snapshot": state
        }

    def restore(self, snapshot):
        return snapshot.get("snapshot")
