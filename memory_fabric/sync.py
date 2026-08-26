from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryEvent:
    source: str
    key: str
    value: dict
    timestamp: datetime


class MemorySynchronizer:
    def __init__(self):
        self.nodes = {}

    def register_node(self, name, storage):
        self.nodes[name] = storage

    async def broadcast(self, event):
        for storage in self.nodes.values():
            await storage.save(event.key, event.value)
