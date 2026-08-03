#!/usr/bin/env python3
"""CLI для жизненного цикла продаж с ТТН.

Примеры:
  python run_sales_lifecycle.py migrate
  python run_sales_lifecycle.py tasks
  python run_sales_lifecycle.py shipped 20451502718405
  python run_sales_lifecycle.py delivered 20451502718405
  python run_sales_lifecycle.py returned 20451502718405
  python run_sales_lifecycle.py return_received 20451502718405

Основной интерфейс для владельца — сообщения Telegram-боту. Этот CLI полезен
для диагностики и безопасных ручных операций на сервере.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.sales_lifecycle import SalesLifecycle

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "tasks"
    reference = " ".join(sys.argv[2:]).strip()
    lifecycle = SalesLifecycle(ROOT)

    if command == "migrate":
        result = lifecycle.migrate_legacy_pending_sales()
    elif command == "tasks":
        result = {"status": "ok", "tasks": lifecycle.list_open_tasks()}
    elif command in ("shipped", "sent"):
        result = lifecycle.mark_shipped(reference, source="cli")
    elif command in ("delivered", "closed"):
        result = lifecycle.mark_delivered(reference, source="cli")
    elif command in ("returned", "return"):
        result = lifecycle.mark_returned(reference, source="cli")
    elif command in ("return_received", "received_return"):
        result = lifecycle.mark_return_received(reference, source="cli")
    elif command == "reminders":
        result = {"status": "ok", "notifications": lifecycle.due_notifications()}
    else:
        result = {"status": "error", "error": "migrate|tasks|shipped|delivered|returned|return_received|reminders"}

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") in ("ok", "ignored") else 1


if __name__ == "__main__":
    raise SystemExit(main())
