"""Safe, local statement parsers used by the A-Банк integration.

Supported inputs are CSV/JSON exports and text-based PDFs converted with the
local ``pdftotext`` utility.  No OCR, browser automation, banking login or
network access is performed here.  Parser errors contain only row/line numbers,
never the original statement payload.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .models import BankTransaction, normalize_currency

_DATE_KEYS = ("booked_at", "date", "operation_date", "transaction_date", "дата", "дата операції", "дата операции")
_AMOUNT_KEYS = ("amount", "value", "sum", "amount_uah", "сума", "сумма", "сума операції", "сумма операции")
_DEBIT_KEYS = ("debit", "дебет", "витрата", "расход")
_CREDIT_KEYS = ("credit", "кредит", "надходження", "приход")
_CURRENCY_KEYS = ("currency", "валюта", "валюта операції", "валюта операции")
_DESCRIPTION_KEYS = ("description", "purpose", "details", "comment", "призначення", "назначение", "опис")
_COUNTERPARTY_KEYS = ("counterparty", "merchant", "recipient", "одержувач", "получатель", "контрагент")
_ID_KEYS = ("transaction_id", "id", "operation_id", "номер операції", "номер операции")


def _lookup(row: Mapping[str, Any], aliases: Iterable[str]) -> Any:
    normalized = {str(key).strip().casefold(): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(alias.casefold())
        if value not in (None, ""):
            return value
    return ""


def parse_amount_minor(value: object) -> int:
    """Parse Ukrainian/European/English money notation into minor units."""
    text = str(value or "").strip().replace("\u00a0", " ")
    if not text:
        raise ValueError("empty amount")
    negative = text.startswith("-") or ("(" in text and ")" in text)
    text = text.replace("₴", "").replace("грн", "").replace("UAH", "")
    text = text.replace("USD", "").replace("EUR", "").replace(" ", "")
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text or text in {"-", ".", ","}:
        raise ValueError("invalid amount")
    if "," in text and "." in text:
        # The last separator is the decimal separator; the other one is a
        # thousands separator.
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) in (1, 2) else "".join(parts)
    elif text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        amount = round(float(text) * 100)
    except ValueError as exc:
        raise ValueError("invalid amount") from exc
    return -abs(amount) if negative else int(amount)


def normalize_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("empty date")
    formats = ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y")
    for fmt in formats:
        try:
            parsed = datetime.strptime(text[:10], fmt).replace(tzinfo=UTC)
            return parsed.date().isoformat()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError("invalid date") from exc


def _transaction_id(row: Mapping[str, Any], index: int, account_id: str, booked_at: str, amount: int, description: str) -> str:
    supplied = str(_lookup(row, _ID_KEYS)).strip()
    if supplied:
        return supplied[:160]
    digest = hashlib.sha256(f"{account_id}|{booked_at}|{amount}|{description}|{index}".encode()).hexdigest()
    return f"manual-{digest[:24]}"


def row_to_transaction(row: Mapping[str, Any], index: int, *, account_id: str = "manual", provider: str = "abank") -> BankTransaction:
    booked_at = normalize_date(_lookup(row, _DATE_KEYS))
    amount_value = _lookup(row, _AMOUNT_KEYS)
    if amount_value in (None, ""):
        credit = _lookup(row, _CREDIT_KEYS)
        debit = _lookup(row, _DEBIT_KEYS)
        if credit not in (None, ""):
            amount_value = credit
        elif debit not in (None, ""):
            amount_value = f"-{debit}"
    amount = parse_amount_minor(amount_value)
    description = str(_lookup(row, _DESCRIPTION_KEYS) or "").strip()[:500]
    counterparty = str(_lookup(row, _COUNTERPARTY_KEYS) or "").strip()[:240]
    currency = normalize_currency(_lookup(row, _CURRENCY_KEYS))
    return BankTransaction(
        transaction_id=_transaction_id(row, index, account_id, booked_at, amount, description),
        account_id=account_id,
        booked_at=booked_at,
        amount_minor=amount,
        currency=currency,
        description=description,
        counterparty=counterparty,
        provider=provider,
        source="manual",
    )


def parse_csv_statement(content: str | bytes, *, account_id: str = "manual", provider: str = "abank") -> tuple[list[BankTransaction], list[dict[str, Any]]]:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    text = str(content)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return [], [{"row": 1, "error": "missing header"}]
    transactions: list[BankTransaction] = []
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=2):
        try:
            transactions.append(row_to_transaction(row, index, account_id=account_id, provider=provider))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})
    return transactions, errors


def parse_json_statement(content: str | bytes, *, account_id: str = "manual", provider: str = "abank") -> tuple[list[BankTransaction], list[dict[str, Any]]]:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    try:
        raw = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return [], [{"row": 1, "error": "invalid JSON"}]
    rows = raw.get("transactions", raw.get("operations", raw.get("items", []))) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return [], [{"row": 1, "error": "JSON must contain a transaction list"}]
    transactions: list[BankTransaction] = []
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            errors.append({"row": index, "error": "transaction must be an object"})
            continue
        try:
            transactions.append(row_to_transaction(row, index, account_id=account_id, provider=provider))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})
    return transactions, errors


def _parse_text_lines(text: str, *, account_id: str = "manual", provider: str = "abank") -> tuple[list[BankTransaction], list[dict[str, Any]]]:
    transactions: list[BankTransaction] = []
    errors: list[dict[str, Any]] = []
    date_pattern = r"(?P<date>\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[./-]\d{2}[./-]\d{2,4})"
    amount_pattern = r"(?P<amount>[+-]?\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:UAH|грн|USD|EUR|₴)?\s*$"
    for index, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or not re.search(date_pattern, line):
            continue
        date_match = re.search(date_pattern, line)
        amount_match = re.search(amount_pattern, line, flags=re.IGNORECASE)
        if not date_match or not amount_match:
            continue
        description = line[date_match.end():amount_match.start()].strip(" |;,-")
        row = {"date": date_match.group("date"), "amount": amount_match.group("amount"), "description": description}
        try:
            transactions.append(row_to_transaction(row, index, account_id=account_id, provider=provider))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})
    return transactions, errors


def parse_pdf_statement(path: str | Path, *, account_id: str = "manual", provider: str = "abank") -> tuple[list[BankTransaction], list[dict[str, Any]]]:
    """Extract text from a local PDF using pdftotext, without OCR/network."""
    path = Path(path)
    if not path.is_file():
        return [], [{"row": 0, "error": "file not found"}]
    if not shutil.which("pdftotext"):
        return [], [{"row": 0, "error": "pdftotext is not installed"}]
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [], [{"row": 0, "error": "local PDF text extraction failed"}]
    if result.returncode != 0:
        return [], [{"row": 0, "error": "local PDF text extraction failed"}]
    return _parse_text_lines(result.stdout, account_id=account_id, provider=provider)
