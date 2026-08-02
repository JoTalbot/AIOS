class BackupManager:
    """Ecosystem backup management foundation."""

    def __init__(self):
        self.backups = []

    def create(self, state):
        self.backups.append(state)

    def latest(self):
        return self.backups[-1] if self.backups else None
