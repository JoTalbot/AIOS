#!/usr/bin/env python3
"""CLI for the metadata-only AIOS phone control center."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.phone_control_center import PhoneControlCenter

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    if command != "status":
        print(json.dumps({"status": "error", "error": "status"}, ensure_ascii=False))
        return 1
    report = PhoneControlCenter(ROOT).snapshot()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
