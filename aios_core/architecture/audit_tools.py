"""Read-only filtering and export for architecture audit records."""

from __future__ import annotations

import json
from typing import Any

from .audit import ArchitectureAuditStore


class AuditQuery:
    def __init__(self, store: ArchitectureAuditStore) -> None:
        self.store = store

    def find(self, *, correlation_id: str | None = None, event: str | None = None) -> list[dict[str, Any]]:
        records = self.store.read()
        if correlation_id is not None:
            records = [item for item in records if item.get("correlation_id") == correlation_id]
        if event is not None:
            records = [item for item in records if item.get("event") == event]
        return records

    def export_json(self, **filters: str) -> str:
        return json.dumps(self.find(**filters), ensure_ascii=False, sort_keys=True)
