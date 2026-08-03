"""Мини-CRM поверх жизненного цикла продаж AIOS.

CRM не создаёт сообщения и не выполняет финансовых операций. Она синхронизирует
уже существующие сделки в карточки клиентов, добавляет безопасные теги и даёт
данные для Dashboard/экспорта.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _phone_mask(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return f"••••{digits[-4:]}" if len(digits) >= 4 else ""


def _customer_identity(sale: dict) -> str:
    phone = re.sub(r"\D", "", str(sale.get("customer_phone") or ""))
    if phone:
        digest = hashlib.sha256(phone.encode()).hexdigest()[:16]
        return f"phone:{digest}"
    platform = str(sale.get("platform") or "").strip().casefold()
    chat = str(sale.get("chat") or "").strip().casefold()
    if platform or chat:
        return f"chat:{platform}:{chat}"
    name = str(sale.get("recipient") or "").strip().casefold()
    if name:
        return "name:" + hashlib.sha256(name.encode()).hexdigest()[:16]
    return "sale:" + str(sale.get("id") or "unknown")


def _derived_tags(sales: list[dict]) -> set[str]:
    statuses = {str(s.get("status") or "") for s in sales}
    tags: set[str] = set()
    if statuses & {"awaiting_shipment", "ttn_created", "in_transit", "returning"}:
        tags.add("активная сделка")
    if "delivered" in statuses:
        tags.add("покупатель")
    if statuses & {"returned", "return_received", "returning"}:
        tags.add("возврат")
    if not tags:
        tags.add("лид")
    return tags


class CRMStore:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root is not None else PROJECT_ROOT
        self.data_dir = self.root / "data"
        self.sales_path = self.data_dir / "sales_lifecycle.json"
        self.path = self.data_dir / "customer_crm.json"

    def _customers(self) -> list[dict]:
        return _read(self.path, [])

    def sync(self) -> dict:
        """Синхронизировать карточки из lifecycle-сделок, сохранив ручные теги/заметки."""
        sales = _read(self.sales_path, [])
        customers = self._customers()
        existing = {str(c.get("id")): c for c in customers if c.get("id")}
        grouped: dict[str, list[dict]] = {}
        for sale in sales:
            if not isinstance(sale, dict):
                continue
            grouped.setdefault(_customer_identity(sale), []).append(sale)

        refreshed: list[dict] = []
        for customer_id, rows in grouped.items():
            previous = existing.get(customer_id, {})
            rows = sorted(rows, key=lambda s: str(s.get("updated_at") or s.get("created_at") or ""))
            latest = rows[-1]
            manual_tags = set(previous.get("manual_tags") or [])
            channels = sorted({str(s.get("platform") or "ручной") for s in rows if s.get("platform")})
            tags = sorted(_derived_tags(rows) | manual_tags)
            delivered = [s for s in rows if s.get("status") == "delivered"]
            active = [s for s in rows if s.get("status") in {"awaiting_shipment", "ttn_created", "in_transit", "returning"}]
            display = str(latest.get("recipient") or latest.get("chat") or "Клиент").strip()[:120]
            refreshed.append({
                "id": customer_id,
                "display_name": display or "Клиент",
                "phone_masked": _phone_mask(str(latest.get("customer_phone") or "")),
                "channels": channels,
                "tags": tags,
                "manual_tags": sorted(manual_tags),
                "note": str(previous.get("note") or "")[:500],
                "sales_ids": [str(s.get("id") or "") for s in rows],
                "sales_count": len(rows),
                "delivered_count": len(delivered),
                "active_count": len(active),
                "lifetime_amount": round(sum(float(s.get("amount") or 0) for s in delivered), 2),
                "last_status": str(latest.get("status") or ""),
                "last_item": str(latest.get("item") or ""),
                "updated_at": str(latest.get("updated_at") or latest.get("created_at") or _now()),
            })
        refreshed.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        _write(self.path, refreshed)
        return {"status": "ok", "customers": refreshed, "count": len(refreshed)}

    def snapshot(self, limit: int = 30) -> dict:
        customers = self.sync().get("customers", [])
        tag_counts: dict[str, int] = {}
        for customer in customers:
            for tag in customer.get("tags") or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return {"status": "ok", "count": len(customers), "tags": tag_counts,
                "customers": customers[:limit]}

    def find(self, query: str) -> dict | None:
        q = (query or "").strip().casefold()
        if not q:
            return None
        for customer in self.snapshot(limit=500).get("customers", []):
            searchable = " ".join([
                str(customer.get("display_name") or ""),
                str(customer.get("last_item") or ""),
                " ".join(customer.get("tags") or []),
            ]).casefold()
            if q in searchable:
                return customer
        return None

    def add_tag(self, customer_id: str, tag: str, note: str = "") -> dict:
        customers = self.sync().get("customers", [])
        for customer in customers:
            if customer.get("id") == customer_id:
                tags = set(customer.get("manual_tags") or [])
                if tag.strip():
                    tags.add(tag.strip()[:50])
                customer["manual_tags"] = sorted(tags)
                customer["tags"] = sorted(set(customer.get("tags") or []) | tags)
                if note.strip():
                    customer["note"] = note.strip()[:500]
                _write(self.path, customers)
                return {"status": "ok", "customer": customer}
        return {"status": "error", "error": "Клиент не найден"}
