from collections import deque


class ExperienceReplay:
    def __init__(self, capacity=1000):
        self.buffer = deque(maxlen=capacity)

    def add(self, experience):
        self.buffer.append(experience)

    def sample(self, limit=10):
        return list(self.buffer)[-limit:]

    def size(self):
        return len(self.buffer)
