class TaskManager:
    """Autonomous task lifecycle foundation."""

    def __init__(self):
        self.tasks = []

    def add(self, task):
        self.tasks.append(task)

    def list(self):
        return self.tasks
