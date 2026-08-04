#!/usr/bin/env python3
"""CLI for metadata-only phone metrics history and CSV export."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.phone_metrics import PhoneMetricsStore

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "trend"
    store = PhoneMetricsStore(ROOT)
    if command == "trend":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
        result = store.trend(limit)
    elif command == "export":
        target = store.export_csv()
        result = {"status": "ok", "file": str(target), "rows": len(store.recent(180))}
    elif command == "recent":
        result = {"status": "ok", "rows": store.recent(30)}
    else:
        result = {"status": "error", "error": "trend [N]|recent|export"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
