"""Episodic memory layer for AIOS agents."""

from datetime import datetime


class EpisodicMemory:
    def __init__(self):
        self.events = []

    def remember(self, agent_id, event, result=None):
        self.events.append({
            "agent": agent_id,
            "event": event,
            "result": result,
            "time": datetime.utcnow().isoformat()
        })

    def recall(self, agent_id=None):
        if agent_id is None:
            return self.events
        return [e for e in self.events if e["agent"] == agent_id]
