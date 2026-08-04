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
    if command != "status":
        print(json.dumps({"status": "error", "error": "status"}, ensure_ascii=False))
        return 1
    print(json.dumps(AndroidBankMonitor(ROOT).snapshot(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
