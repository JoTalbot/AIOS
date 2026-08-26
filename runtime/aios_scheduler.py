"""AIOS task scheduler."""

from collections import defaultdict


class AIOSScheduler:
    def __init__(self):
        self.queue = []

    def add_task(self, task, priority=0):
        self.queue.append({"task": task, "priority": priority})
        self.queue.sort(key=lambda item: item["priority"], reverse=True)

    def next_task(self):
        return self.queue.pop(0) if self.queue else None
