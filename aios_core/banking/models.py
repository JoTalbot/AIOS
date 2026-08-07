"""Provider-neutral, read-only banking models for AIOS.

The models intentionally contain no credentials, card PANs, OTPs or raw provider
payloads.  Amounts are stored as signed integer minor units (for example, kopecks).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class BankAccount:
    provider: str
    account_id: str
    name: str = ""
    currency: str = "UAH"
    masked_identifier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BankTransaction:
    transaction_id: str
    account_id: str
    booked_at: str
    amount_minor: int
    currency: str = "UAH"
    description: str = ""
    counterparty: str = ""
    provider: str = "manual"
    source: str = "manual"

    @property
    def direction(self) -> str:
        if self.amount_minor > 0:
            return "credit"
        if self.amount_minor < 0:
            return "debit"
        return "neutral"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["direction"] = self.direction
        return data


@dataclass(frozen=True)
class ConsentStatus:
    provider: str
    status: str = "not_configured"
    scopes: tuple[str, ...] = ()
    expires_at: str | None = None
    read_only: bool = True
    revocable: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scopes"] = list(self.scopes)
        return data


@dataclass(frozen=True)
class ImportResult:
    status: str
    format: str
    imported: int
    skipped: int
    errors: tuple[dict[str, Any], ...] = ()
    source: str = "manual"
    imported_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["errors"] = list(self.errors)
        return data


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def normalize_currency(value: object, default: str = "UAH") -> str:
    text = str(value or default).strip().upper()
    aliases = {"ГРН": "UAH", "UAH": "UAH", "₴": "UAH", "ДОЛ": "USD", "$": "USD"}
    return aliases.get(text, text[:8] or default)
