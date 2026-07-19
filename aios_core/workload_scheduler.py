"""
AIOS Workload Scheduler Layer v2.1.1

Schedules tasks according to priority and available resources.
"""


class WorkloadScheduler:
    def __init__(self):
        self.queue = []

    def add_task(self, task: dict):
        self.queue.append(task)
        return task

    def pending(self):
        return self.queue
