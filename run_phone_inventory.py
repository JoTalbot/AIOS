#!/usr/bin/env python3
"""CLI for safe Android/Companion inventory metadata."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.phone_inventory import PhoneInventory

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "record"
    inventory = PhoneInventory(ROOT)
    result = inventory.latest() if mode == "latest" else inventory.record()
    print(json.dumps(result, ensure_ascii=False, indent=2))
