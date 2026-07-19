"""AIOS Memory Manager Layer v2.1.1

Manages AIOS memory lifecycle and retrieval across constitutional, operational
and personal categories.
"""


class MemoryManager:
    """Manages memory storage and retrieval."""

    def __init__(self):
        self.memory = {}
        self.categories = {
            "personal": {},       # User-controlled
            "operational": {},    # System operations
            "constitutional": {},# Immutable principles
        }

    def store(self, item: dict, category: str = "operational"):
        """Store a memory item under a category."""
        if category not in self.categories:
            category = "operational"

        item_id = len(self.memory)
        entry = dict(item)
        entry["_category"] = category
        self.memory[item_id] = entry
        self.categories[category][item_id] = entry
        return {"id": item_id, "stored": True, "category": category}

    def search(self, query: str) -> list:
        """Search memory items whose string form contains ``query``."""
        results = []
        for item in self.memory.values():
            if query and query in str(item):
                results.append(item)
        return results

    def retrieve(self, item_id: int) -> dict:
        """Retrieve a memory item by id."""
        return self.memory.get(item_id)

    def list_category(self, category: str) -> dict:
        """Return all items in a category."""
        return self.categories.get(category, {})

    def size(self) -> int:
        """Total number of stored items."""
        return len(self.memory)
