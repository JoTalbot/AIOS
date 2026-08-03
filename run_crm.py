#!/usr/bin/env python3
"""CLI для CRM поверх lifecycle-продаж.

  python run_crm.py summary
  python run_crm.py customers [N]
  python run_crm.py find <запрос>
  python run_crm.py tag <customer_id> <тег> [заметка]
  python run_crm.py export
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from aios_core.crm import CRMStore

ROOT = Path(__file__).resolve().parent


def export_csv(store: CRMStore) -> dict:
    snapshot = store.snapshot(limit=10000)
    dest_dir = ROOT / "data" / "exports"
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"crm_customers_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ')}.csv"
    fields = ["display_name", "phone_masked", "channels", "tags", "sales_count", "delivered_count",
              "active_count", "lifetime_amount", "last_status", "last_item", "updated_at", "note"]
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for customer in snapshot.get("customers", []):
            writer.writerow({
                "display_name": customer.get("display_name", ""),
                "phone_masked": customer.get("phone_masked", ""),
                "channels": ", ".join(customer.get("channels") or []),
                "tags": ", ".join(customer.get("tags") or []),
                "sales_count": customer.get("sales_count", 0),
                "delivered_count": customer.get("delivered_count", 0),
                "active_count": customer.get("active_count", 0),
                "lifetime_amount": customer.get("lifetime_amount", 0),
                "last_status": customer.get("last_status", ""),
                "last_item": customer.get("last_item", ""),
                "updated_at": customer.get("updated_at", ""),
                "note": customer.get("note", ""),
            })
    return {"status": "ok", "file": str(path), "rows": len(snapshot.get("customers", []))}


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "summary"
    store = CRMStore(ROOT)
    if command == "sync":
        result = store.sync()
    elif command == "summary":
        result = store.snapshot(limit=10)
    elif command == "customers":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        result = store.snapshot(limit=limit)
    elif command == "find" and len(sys.argv) > 2:
        found = store.find(" ".join(sys.argv[2:]))
        result = {"status": "ok", "customer": found} if found else {"status": "error", "error": "Клиент не найден"}
    elif command == "tag" and len(sys.argv) >= 4:
        result = store.add_tag(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    elif command == "export":
        result = export_csv(store)
    else:
        result = {"status": "error", "error": "sync|summary|customers|find|tag|export"}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
