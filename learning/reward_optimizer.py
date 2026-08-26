"""Reward based optimization for AIOS strategies."""


class RewardOptimizer:
    def __init__(self):
        self.rewards = {}

    def update(self, strategy, reward):
        self.rewards[strategy] = reward

    def best(self):
        if not self.rewards:
            return None
        return max(self.rewards, key=self.rewards.get)
