"""AIOS Runtime Recovery Manager."""

class RecoveryManager:
    def __init__(self):
        self.failures = []

    def record_failure(self, task_id, error):
        self.failures.append({"task_id": task_id, "error": str(error)})

    def last_failure(self):
        return self.failures[-1] if self.failures else None

    def can_retry(self, task_id):
        return True
