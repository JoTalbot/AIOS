"""High-level safe A-Банк integration service."""
from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .business import ABankBusinessAPI
from .models import BankTransaction, ImportResult, utc_now
from .open_banking import DisabledOpenBankingProvider, OpenBankingConfig, ReadOnlyProvider
from .parsers import parse_csv_statement, parse_json_statement, parse_pdf_statement
from .store import BankingStore


class BankingService:
    """Combines read-only provider metadata, manual imports and local storage."""

    def __init__(self, root: str | Path | None = None, provider: ReadOnlyProvider | None = None):
        data_root = root or os.getenv("AIOS_BANKING_DATA", "data/banking")
        self.store = BankingStore(data_root)
        self.config = OpenBankingConfig.from_env()
        self.provider = provider or DisabledOpenBankingProvider(self.config)
        self.business_api = ABankBusinessAPI()

    def status(self, subject: str) -> dict[str, Any]:
        provider_status = self.provider.status() if hasattr(self.provider, "status") else self.config.status()
        return {
            "status": "ok",
            "provider": "abank",
            "personal_finance": {
                **provider_status,
                "consent": self.provider.consent_status().to_dict(),
            },
            "manual_import": {
                "csv": True,
                "json": True,
                "pdf_text": True,
                "ocr": False,
                "network": False,
            },
            "business_api": self.business_api.safety_status(),
            "local_store": self.store.summary(subject),
            "automation_policy": {
                "read_only": True,
                "payments": False,
                "transfers": False,
                "card_management": False,
                "bank_app_automation": False,
                "mitm": False,
            },
        }

    def import_content(self, subject: str, content: str | bytes, *, format: str, account_id: str = "manual") -> ImportResult:
        format = str(format or "").strip().lower()
        if format == "csv":
            transactions, errors = parse_csv_statement(content, account_id=account_id)
        elif format == "json":
            transactions, errors = parse_json_statement(content, account_id=account_id)
        else:
            raise ValueError("format must be csv or json for content imports")
        imported = self.store.upsert_transactions(subject, transactions)
        result = ImportResult(
            status="ok" if not errors else "partial",
            format=format,
            imported=imported,
            skipped=len(errors),
            errors=tuple(errors[:50]),
            source="manual",
            imported_at=utc_now(),
        )
        self.store.record_import(subject, result)
        return result

    def import_pdf(self, subject: str, path: str | Path, *, account_id: str = "manual") -> ImportResult:
        transactions, errors = parse_pdf_statement(path, account_id=account_id)
        imported = self.store.upsert_transactions(subject, transactions)
        result = ImportResult(
            status="ok" if not errors else "partial",
            format="pdf",
            imported=imported,
            skipped=len(errors),
            errors=tuple(errors[:50]),
            source="manual",
            imported_at=utc_now(),
        )
        self.store.record_import(subject, result)
        return result

    def list_transactions(self, subject: str, *, limit: int = 100, since: str | None = None) -> list[dict[str, Any]]:
        return self.store.list_transactions(subject, limit=limit, since=since)

    def sync_from_provider(self, subject: str, *, account_ids: Sequence[str] | None = None, since: str | None = None) -> dict[str, Any]:
        """Persist data from an injected authorized provider; default provider is empty.

        This method accepts only normalized models from the provider boundary.
        It does not perform OAuth, open a bank app or call arbitrary URLs.
        """
        accounts = list(self.provider.list_accounts())
        selected = set(account_ids or [account.account_id for account in accounts])
        transactions: list[BankTransaction] = []
        for account in accounts:
            if account.account_id not in selected:
                continue
            transactions.extend(self.provider.list_transactions(account.account_id, since=since))
        imported = self.store.upsert_transactions(subject, transactions)
        return {
            "status": "ok",
            "accounts_seen": len(accounts),
            "transactions_seen": len(transactions),
            "transactions_imported": imported,
            "read_only": True,
            "network_called": False,
        }
