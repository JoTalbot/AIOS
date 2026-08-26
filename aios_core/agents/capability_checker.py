"""Capability validation for AIOS agents."""
class CapabilityChecker:
    def can_execute(self, agent, action):
        return action in getattr(agent, 'skills', [])
