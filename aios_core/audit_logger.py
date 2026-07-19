"""AIOS Audit Logger v2.1.1

Stores constitutional decisions and execution events.
"""

import json
from datetime import datetime, timezone


class AuditLogger:
    """Logs all constitutional decisions and execution events."""

    def __init__(self, file_path="audit_log.jsonl"):
        self.file_path = file_path
        self.events = []

    def record(self, event: dict):
        """Record an audit event."""
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.events.append(event)
        
        # Also write to file
        try:
            with open(self.file_path, "a", encoding="utf-8") as log:
                log.write(json.dumps(event, ensure_ascii=False) + "\n")
        except (IOError, OSError):
            pass  # Log to memory if file write fails
        
        return event

    def query(self, event_type: str = None) -> list:
        """Query audit log."""
        if event_type:
            return [e for e in self.events if e.get("type") == event_type]
        return self.events
