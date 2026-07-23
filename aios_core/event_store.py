"""Event Store for Event Sourcing in AIOS"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List


class EventStore:
    """Simple in-memory + file-based event store."""

    def __init__(self, storage_path: str = "events.jsonl"):
        self.storage_path = storage_path
        self.events: List[Dict] = []

    def append(self, event_type: str, data: dict[str, Any], aggregate_id: str = None) -> str:
        """Execute append."""
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": data,
            "aggregate_id": aggregate_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)

        # Persist to file
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event["id"]

    def get_events(self, aggregate_id: str = None) -> List[Dict]:
        """Execute get events."""
        if aggregate_id:
            return [e for e in self.events if e.get("aggregate_id") == aggregate_id]
        return self.events.copy()

    def replay(self, aggregate_id: str) -> Dict:
        """Rebuild state from events."""
        events = self.get_events(aggregate_id)
        state = {}
        for event in events:
            state.update(event.get("data", {}))
        return state

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"total_events": len(self.events), "storage": self.storage_path}
