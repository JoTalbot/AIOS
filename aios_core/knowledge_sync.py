"""
AIOS Knowledge Sync Layer v2.1.1

Synchronizes approved knowledge patterns between nodes.
"""


class KnowledgeSync:
    def __init__(self):
        self.records = []

    def add_pattern(self, pattern: dict):
        self.records.append(pattern)
        return pattern

    def export_allowed(self, classification: str) -> bool:
        return classification in ["operational", "constitutional"]
