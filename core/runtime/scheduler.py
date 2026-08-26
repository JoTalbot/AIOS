"""AIOS task scheduler.

Coordinates execution ordering and prepares tasks for runtime workers.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ScheduledTask:
    task_id: str
    payload: Any


class TaskScheduler:
    def __init__(self):
        self.queue = []

    def submit(self, task: ScheduledTask):
        self.queue.append(task)

    def next_task(self):
        if not self.queue:
            return None
        return self.queue.pop(0)
