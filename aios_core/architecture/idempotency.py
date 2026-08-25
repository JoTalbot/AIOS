"""In-memory idempotency state for governed action retries."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    fingerprint: str
    result: Any


class IdempotencyLedger:
    def __init__(self) -> None:
        self.records: dict[str, IdempotencyRecord] = {}

    def record(self, key: str, fingerprint: str, result: Any) -> IdempotencyRecord:
        existing = self.records.get(key)
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise RuntimeError("idempotency key reused with different request")
            return existing
        record = IdempotencyRecord(key, fingerprint, result)
        self.records[key] = record
        return record

    def lookup(self, key: str, fingerprint: str) -> Any | None:
        record = self.records.get(key)
        if record is None:
            return None
        if record.fingerprint != fingerprint:
            raise RuntimeError("idempotency fingerprint mismatch")
        return record.result
