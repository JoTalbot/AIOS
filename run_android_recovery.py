#!/usr/bin/env python3
"""CLI: diagnose Android recovery without exposing endpoint/screen data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.android_recovery import AndroidRecovery

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    if command != "check":
        print(json.dumps({"status": "error", "error": "check"}, ensure_ascii=False))
        return 1
    result = AndroidRecovery(ROOT).check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
