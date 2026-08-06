"""Read-only Open Banking capability boundary for A-Банк.

A real provider must be an authorized AISP/PISP and must supply data through the
official Open Banking interface.  This module intentionally does not implement
login scraping, password handling, network interception or payment initiation.
The provider is injected, which keeps the production default disabled until an
official provider contract and certificate are configured.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .models import BankAccount, BankTransaction, ConsentStatus

READ_ONLY_SCOPES = frozenset({"accounts:read", "balances:read", "transactions:read"})
WRITE_SCOPES = frozenset({"payments:write", "transfers:write", "cards:write"})


class ReadOnlyProvider(Protocol):
    """Minimal provider contract for an authorized AISP or aggregator."""

    def list_accounts(self) -> Sequence[BankAccount]: ...

    def list_transactions(self, account_id: str, since: str | None = None) -> Sequence[BankTransaction]: ...

    def consent_status(self) -> ConsentStatus: ...


@dataclass(frozen=True)
class OpenBankingConfig:
    provider_name: str = "not_configured"
    enabled: bool = False
    scopes: tuple[str, ...] = tuple(sorted(READ_ONLY_SCOPES))
    consent_url_configured: bool = False

    @classmethod
    def from_env(cls) -> OpenBankingConfig:
        raw_scopes = tuple(item.strip() for item in os.getenv("AIOS_ABANK_OPEN_BANKING_SCOPES", "").split(",") if item.strip())
        scopes = raw_scopes or tuple(sorted(READ_ONLY_SCOPES))
        # Never accept write scopes in the personal-finance adapter.
        scopes = tuple(scope for scope in scopes if scope in READ_ONLY_SCOPES)
        return cls(
            provider_name=os.getenv("AIOS_ABANK_OPEN_BANKING_PROVIDER", "not_configured"),
            enabled=os.getenv("AIOS_ABANK_OPEN_BANKING_ENABLED", "0") == "1",
            scopes=scopes,
            consent_url_configured=bool(os.getenv("AIOS_ABANK_OPEN_BANKING_CONSENT_URL", "").strip()),
        )

    def status(self) -> dict[str, Any]:
        if not self.enabled:
            state = "disabled"
        elif self.provider_name == "not_configured":
            state = "awaiting_provider"
        else:
            state = "configured_read_only"
        return {
            "status": state,
            "provider": self.provider_name,
            "enabled": self.enabled,
            "scopes": list(self.scopes),
            "read_only": True,
            "write_scopes_accepted": False,
            "consent_url_configured": self.consent_url_configured,
            "network_sync": False,
            "reason": "Official AISP/aggregator and consent flow must be configured before live sync.",
        }


class DisabledOpenBankingProvider:
    """Default provider: reports capability without touching a bank."""

    def __init__(self, config: OpenBankingConfig | None = None):
        self.config = config or OpenBankingConfig.from_env()

    def list_accounts(self) -> Sequence[BankAccount]:
        return ()

    def list_transactions(self, account_id: str, since: str | None = None) -> Sequence[BankTransaction]:
        return ()

    def consent_status(self) -> ConsentStatus:
        return ConsentStatus(
            provider=self.config.provider_name,
            status="not_configured" if self.config.provider_name == "not_configured" else "not_granted",
            scopes=self.config.scopes,
            read_only=True,
            revocable=True,
        )

    def status(self) -> dict[str, Any]:
        return self.config.status()


def validate_scopes(scopes: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(scope).strip() for scope in scopes if str(scope).strip()))
    forbidden = sorted(set(normalized) & WRITE_SCOPES)
    if forbidden:
        raise ValueError("write scopes are forbidden in the A-Банк read-only adapter")
    unknown = sorted(set(normalized) - READ_ONLY_SCOPES)
    if unknown:
        raise ValueError(f"unsupported Open Banking scopes: {', '.join(unknown)}")
    return normalized
