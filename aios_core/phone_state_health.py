"""Metadata-only integrity/freshness health for Android AIOS state files."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


STATE_FILES = (
    "notifications.json",
    "lead_candidates.json",
    "bank_notification_tasks.json",
    "action_audit.json",
    "app_ui_calibrations.json",
    "recovery.json",
    "control_history.json",
)


def _service_active(name: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", name], check=False).returncode == 0


def _age_minutes(path: Path) -> int | None:
    try:
        return max(0, int((datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 60))
    except OSError:
        return None


def _backup_age_hours(root: Path) -> float | None:
    base = root / "backups" / "messenger_profiles"
    try:
        archives = [path / "profiles.tar.gz" for path in base.iterdir() if path.is_dir() and (path / "profiles.tar.gz").exists()]
        latest = max(archives, key=lambda path: path.stat().st_mtime)
        return round((datetime.now(timezone.utc).timestamp() - latest.stat().st_mtime) / 3600, 1)
    except Exception:
        return None


class PhoneStateHealth:
    """Check state integrity without reading/reporting payload contents."""

    def __init__(self, root: Path | str, service_probe: Callable[[str], bool] = _service_active):
        self.root = Path(root)
        self.data = self.root / "data" / "android_gateway"
        self.service_probe = service_probe

    def snapshot(self) -> dict:
        rows = []
        invalid = []
        total_bytes = 0
        for name in STATE_FILES:
            path = self.data / name
            exists = path.exists()
            size = 0
            valid = True
            if exists:
                try:
                    size = path.stat().st_size
                    total_bytes += size
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    valid = False
                    invalid.append(name)
            rows.append({"name": name, "exists": exists, "valid": valid, "age_minutes": _age_minutes(path), "bytes": size})
        backup_age = _backup_age_hours(self.root)
        wireguard = bool(self.service_probe("wg-quick@wg0.service"))
        status = "ok" if not invalid and wireguard else "degraded"
        return {
            "status": status,
            "invalid": invalid,
            "files": rows,
            "total_bytes": total_bytes,
            "backup_age_hours": backup_age,
            "wireguard_active": wireguard,
        }
