class RecoveryManager:
    def __init__(self):
        self.snapshots = {}

    def checkpoint(self, workflow_id, state):
        self.snapshots[workflow_id] = state

    def restore(self, workflow_id):
        return self.snapshots.get(workflow_id)
