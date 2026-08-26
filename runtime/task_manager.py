"""Task management layer for AIOS runtime."""

from enum import Enum


class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskManager:
    def __init__(self):
        self.tasks = {}

    def add(self, task_id, payload):
        self.tasks[task_id] = {
            "payload": payload,
            "status": TaskStatus.CREATED
        }

    def update_status(self, task_id, status):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status

    def get(self, task_id):
        return self.tasks.get(task_id)
