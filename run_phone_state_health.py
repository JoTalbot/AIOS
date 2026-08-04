#!/usr/bin/env python3
"""CLI for metadata-only Android state health."""
from __future__ import annotations

import json
from pathlib import Path

from aios_core.phone_state_health import PhoneStateHealth

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    print(json.dumps(PhoneStateHealth(ROOT).snapshot(), ensure_ascii=False, indent=2))
