"""Persistent storage foundation for Agent Memory v2."""

import json
from pathlib import Path


class MemoryPersistence:
    """Simple persistence layer for agent memory snapshots."""

    def __init__(self, storage_path="agent_memory.json"):
        self.storage_path = Path(storage_path)

    def save(self, memory: dict):
        self.storage_path.write_text(
            json.dumps(memory, indent=2),
            encoding="utf-8",
        )

    def load(self) -> dict:
        if not self.storage_path.exists():
            return {}

        return json.loads(
            self.storage_path.read_text(encoding="utf-8")
        )

    def restore_context(self, key: str):
        return self.load().get(key)
