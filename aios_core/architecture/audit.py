"""Persistent hash-chained JSONL audit for architecture decisions and effects."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ArchitectureAuditStore:
    """Append structured events whose hashes bind the complete prior chain."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        event: str,
        *,
        task_id: str,
        action_id: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        records = self.read()
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "correlation_id": f"{task_id}:{action_id}",
            "task_id": task_id,
            "action_id": action_id,
            "agent_id": agent_id,
            "payload": payload or {},
            "previous_hash": records[-1]["hash"] if records else "",
        }
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record["hash"] = hashlib.sha256(encoded.encode()).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        return dict(record)

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]

    def verify(self) -> bool:
        previous_hash = ""
        for stored in self.read():
            record = dict(stored)
            expected_hash = record.pop("hash", "")
            if record.get("previous_hash") != previous_hash:
                return False
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if hashlib.sha256(encoded.encode()).hexdigest() != expected_hash:
                return False
            previous_hash = expected_hash
        return True
