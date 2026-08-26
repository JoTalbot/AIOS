class RollbackController:

    def __init__(self):
        self.snapshots = []

    def save(self, state):
        self.snapshots.append(state)

    def rollback(self):
        if not self.snapshots:
            return None
        return self.snapshots.pop()
