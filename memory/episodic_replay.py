"""Episodic replay for AIOS learning cycles."""

from collections import deque


class EpisodicReplay:
    def __init__(self, capacity=1000):
        self.episodes = deque(maxlen=capacity)

    def store(self, episode):
        self.episodes.append(episode)

    def sample(self, limit=10):
        return list(self.episodes)[-limit:]

    def size(self):
        return len(self.episodes)
