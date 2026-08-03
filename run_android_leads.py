#!/usr/bin/env python3
"""CLI для приватной очереди потенциальных лидов из Android-уведомлений."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.android_leads import AndroidLeadQueue

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "summary"
    queue = AndroidLeadQueue(ROOT)
    if command == "sync":
        result = queue.sync()
    elif command == "summary":
        result = queue.summary()
    elif command == "list":
        source = " ".join(sys.argv[2:]).strip()
        result = {"status": "ok", "leads": queue.list_pending(source=source)}
    elif command == "review" and len(sys.argv) >= 3:
        result = queue.review(sys.argv[2])
    elif command == "promote" and len(sys.argv) >= 3:
        result = queue.promote_to_crm_task(sys.argv[2])
    elif command == "tasks":
        result = {"status": "ok", "tasks": queue.list_crm_tasks()}
    elif command == "complete" and len(sys.argv) >= 3:
        result = queue.complete_crm_task(sys.argv[2])
    else:
        result = {"status": "error", "error": "sync|summary|list [source]|review <id>|promote <id>|tasks|complete <task_id>"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in ("ok", "reviewed", "already_reviewed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
