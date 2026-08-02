class TaskManager:
    """AIOS task management foundation."""

    def __init__(self):
        self.tasks = []

    def add(self, task):
        self.tasks.append(task)

    def list(self):
        return self.tasks
