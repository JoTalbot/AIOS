#!/usr/bin/env python3
"""CLI for metadata-only phone synchronization freshness."""
from __future__ import annotations

import json
from pathlib import Path

from aios_core.phone_sync_status import PhoneSyncStatus

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    print(json.dumps(PhoneSyncStatus(ROOT).snapshot(), ensure_ascii=False, indent=2))
