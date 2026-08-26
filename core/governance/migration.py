class RuntimeMigrationManager:

    def __init__(self):
        self.history = []

    def migrate(self, old_state, new_state):
        record = {
            "from": old_state,
            "to": new_state
        }
        self.history.append(record)
        return record
