#!/usr/bin/env python3
"""CLI for safe Android bank app monitoring."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.android_bank_monitor import AndroidBankMonitor

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    monitor = AndroidBankMonitor(ROOT)
    if command == "status":
        result = monitor.snapshot()
    elif command == "bootstrap":
        result = monitor.bootstrap()
    elif command == "sync":
        result = monitor.sync_tasks()
    elif command == "tasks":
        result = {"status": "ok", "tasks": monitor.list_tasks()}
    elif command == "review" and len(sys.argv) >= 3:
        result = monitor.review_task(sys.argv[2])
    else:
        result = {"status": "error", "error": "status|bootstrap|sync|tasks|review <id>"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in ("ok", "reviewed", "already_reviewed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
