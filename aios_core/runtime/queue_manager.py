"""AIOS execution queue manager."""

from collections import deque


class QueueManager:
    def __init__(self):
        self.queue = deque()

    def push(self, task):
        self.queue.append(task)

    def pop(self):
        if not self.queue:
            return None
        return self.queue.popleft()

    def size(self):
        return len(self.queue)
