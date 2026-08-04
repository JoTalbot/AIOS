#!/usr/bin/env python3
"""Create a token-free, metadata-only Android configuration snapshot."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from aios_core.phone_control_center import PhoneControlCenter
from aios_core.phone_inventory import PhoneInventory

ROOT = Path(__file__).resolve().parent
BACKUPS = ROOT / "backups" / "android_config"
KEEP = 14


def main() -> int:
    inventory = PhoneInventory(ROOT).record()
    control = PhoneControlCenter(ROOT).snapshot()
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inventory": {
            key: inventory.get(key)
            for key in ("android", "sdk", "companion_version", "wireguard_active", "apps_available", "apps_calibrated", "calibrations_stale", "availability_drift", "version_drift")
        },
        "control": {
            "leads": control.get("leads"), "bank_tasks": control.get("bank_tasks"),
            "templates": control.get("templates"), "timers": control.get("timers"),
            "state_health": control.get("state_health"), "recovery": control.get("recovery"),
        },
    }
    BACKUPS.mkdir(parents=True, exist_ok=True)
    path = BACKUPS / f"android_config_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    path.chmod(0o600)
    snapshots = sorted(BACKUPS.glob("android_config_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for stale in snapshots[KEEP:]:
        stale.unlink(missing_ok=True)
    print(json.dumps({"status": "ok", "file": str(path), "kept": min(len(snapshots), KEEP)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
