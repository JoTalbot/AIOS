"""Adaptive agent routing for AIOS v20.7."""


class AdaptiveRouter:
    def select(self, agents, reputations=None):
        if not agents:
            return None
        if reputations:
            return max(agents, key=lambda a: reputations.get(a, 0))
        return agents[0]
