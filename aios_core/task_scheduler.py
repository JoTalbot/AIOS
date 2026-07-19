"""
AIOS Task Scheduler Layer v2.1.1

Schedules and manages AIOS tasks.
"""


class TaskScheduler:
    def __init__(self):
        self.tasks = []

    def schedule(self, task: dict):
        self.tasks.append(task)
        return task

    def list_tasks(self):
        return self.tasks
