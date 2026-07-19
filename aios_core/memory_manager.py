"""AIOS Memory Manager Layer v2.1.1

Manages AIOS memory lifecycle and retrieval.
"""


class MemoryManager:
    """Manages memory storage and retrieval."""

    def __init__(self):
        self.memory = {}
        self.categories = {
            "personal": {},      # User-controlled
            "operational": {},   # System operations
            "constitutional": {} # Immutable principles
        }

    def store(self, item: dict, category: str = "operational"):
        """Store a memory item."""
        if category not in self.categories:
            category = "operational"
        
        item_id = len(self.memory)
        self.memory[item_id] = item
        self.categories[category][item_id] = item
        return {"id": item_id, "stored": True}

    def search(self, query: str) -> list:
        """Search memory."""
        results = []
        for item_id, item in self.memory.items():
            if query in str(item):
                results.append(item)
        return results

    def retrieve(self, item_id: int) -> dict:
        """Retrieve a memory item."""
        return self.memory.get(item_id)
