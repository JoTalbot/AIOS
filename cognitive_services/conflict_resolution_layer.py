"""AIOS v23.9 Conflict Resolution Layer.

Provides a minimal interface for resolving competing agent proposals.
"""


class ConflictResolutionLayer:
    def __init__(self):
        self.conflicts = []

    def register_conflict(self, proposals):
        self.conflicts.append(proposals)
        return proposals

    def resolve(self, proposals):
        if not proposals:
            return None
        return max(proposals, key=lambda item: item.get("confidence", 0))
