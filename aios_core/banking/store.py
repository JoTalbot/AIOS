"""Root-only local storage for imported read-only banking data."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from .models import BankTransaction, ConsentStatus, ImportResult, utc_now

_MAX_TRANSACTIONS = 20_000
_SUBJECT_RE = re.compile(r"^[A-Za-z0-9_.:@+-]{1,160}$")


class BankingStore:
    """Small atomic JSON store with hashed subject partitions.

    It deliberately does not persist bank credentials, bearer tokens, card
    numbers, raw CSV/PDF content or notification text.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with suppress(OSError):
            self.root.chmod(0o700)

    @staticmethod
    def _subject_key(subject: str) -> str:
        value = str(subject or "").strip()
        if not _SUBJECT_RE.fullmatch(value):
            raise ValueError("invalid subject")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]

    def _path(self, subject: str) -> Path:
        return self.root / f"subject-{self._subject_key(subject)}.json"

    def _read(self, subject: str) -> dict[str, Any]:
        path = self._path(subject)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {"transactions": [], "imports": [], "consent": None}
        if not isinstance(value, dict):
            return {"transactions": [], "imports": [], "consent": None}
        value.setdefault("transactions", [])
        value.setdefault("imports", [])
        value.setdefault("consent", None)
        return value

    def _write(self, subject: str, value: dict[str, Any]) -> None:
        path = self._path(subject)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(self.root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, path)
            os.chmod(path, 0o600)
        finally:
            with suppress(FileNotFoundError):
                os.unlink(temporary_name)

    def upsert_transactions(self, subject: str, transactions: list[BankTransaction]) -> int:
        state = self._read(subject)
        existing = {str(item.get("transaction_id")): item for item in state["transactions"] if isinstance(item, dict)}
        before = len(existing)
        for transaction in transactions:
            existing[transaction.transaction_id] = transaction.to_dict()
        ordered = sorted(existing.values(), key=lambda item: (str(item.get("booked_at", "")), str(item.get("transaction_id", ""))))
        state["transactions"] = ordered[-_MAX_TRANSACTIONS:]
        self._write(subject, state)
        return max(0, len(existing) - before)

    def list_transactions(self, subject: str, *, limit: int = 100, since: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        rows = [item for item in self._read(subject)["transactions"] if isinstance(item, dict)]
        if since:
            rows = [item for item in rows if str(item.get("booked_at", "")) >= since]
        return list(reversed(rows[-limit:]))

    def summary(self, subject: str) -> dict[str, Any]:
        state = self._read(subject)
        rows = [item for item in state["transactions"] if isinstance(item, dict)]
        return {
            "transactions": len(rows),
            "imports": len([item for item in state["imports"] if isinstance(item, dict)]),
            "consent": state.get("consent") or ConsentStatus(provider="abank").to_dict(),
        }

    def record_import(self, subject: str, result: ImportResult) -> None:
        state = self._read(subject)
        state["imports"].append({
            "format": result.format,
            "source": result.source,
            "imported": result.imported,
            "skipped": result.skipped,
            "error_count": len(result.errors),
            "imported_at": result.imported_at or utc_now(),
        })
        state["imports"] = state["imports"][-100:]
        self._write(subject, state)

    def set_consent(self, subject: str, consent: ConsentStatus) -> None:
        # This method only records a consent status received from an official
        # provider. It cannot grant consent or create a banking session.
        state = self._read(subject)
        state["consent"] = consent.to_dict()
        self._write(subject, state)

    def clear_subject(self, subject: str) -> None:
        with suppress(FileNotFoundError):
            self._path(subject).unlink()
