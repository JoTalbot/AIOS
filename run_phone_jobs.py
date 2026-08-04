#!/usr/bin/env python3
"""CLI for scheduled Android job manifest/status/dry-run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.phone_jobs import PhoneJobs

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    jobs = PhoneJobs(ROOT)
    result = jobs.dry_run() if command == "dry-run" else jobs.snapshot() if command == "status" else {"status": "error", "error": "status|dry-run"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("status") == "ok" else 1)
