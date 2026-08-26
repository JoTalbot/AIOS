class AutoRecoveryManager:
    def __init__(self):
        self.history = []

    def recover(self, system):
        result = {
            "system": system,
            "status": "recovered"
        }
        self.history.append(result)
        return result
