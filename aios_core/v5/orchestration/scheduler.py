class TaskScheduler:
    """Task scheduling foundation for AIOS agents."""

    def __init__(self):
        self.queue = []

    def add(self, task):
        self.queue.append(task)

    def next(self):
        return self.queue.pop(0) if self.queue else None
