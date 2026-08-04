"""Manifest, health and dry-run checks for scheduled Android AIOS jobs."""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


JOBS = (
    ("notifications", "aios-android-notifications.timer", "run_android_notification_collector.py"),
    ("lead_digest", "aios-android-leads.timer", "run_android_lead_digest.py"),
    ("daily_digest", "aios-phone-control-digest.timer", "run_phone_control_digest.py"),
    ("weekly_report", "aios-phone-weekly-report.timer", "run_phone_weekly_report.py"),
    ("inventory", "aios-phone-inventory.timer", "run_phone_inventory_alert.py"),
    ("config_backup", "aios-android-config-backup.timer", "run_android_config_backup.py"),
    ("ops_health", "aios-ops-health.timer", "run_ops_health.py"),
)
MAX_HISTORY = 180


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _service_active(name: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", name], check=False).returncode == 0


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class PhoneJobs:
    """Jobs state does not execute jobs or inspect private job payloads."""

    def __init__(self, root: Path | str, service_probe: Callable[[str], bool] = _service_active):
        self.root = Path(root)
        self.service_probe = service_probe
        self.path = self.root / "data" / "android_gateway" / "job_health_history.json"

    def _backup_status(self) -> dict:
        directory = self.root / "backups" / "android_config"
        files = sorted(directory.glob("android_config_*.json")) if directory.exists() else []
        invalid = 0
        for path in files:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                invalid += 1
        return {"count": len(files), "retention_ok": len(files) <= 14, "invalid": invalid}

    def snapshot(self, record: bool = True) -> dict:
        rows = []
        for job_id, unit, script in JOBS:
            rows.append({
                "id": job_id,
                "unit": unit,
                "active": bool(self.service_probe(unit)),
                "script": script,
                "script_exists": (self.root / script).exists(),
            })
        backup = self._backup_status()
        report = {
            "status": "ok" if all(row["active"] and row["script_exists"] for row in rows) and backup["retention_ok"] and not backup["invalid"] else "degraded",
            "checked_at": _now(),
            "jobs": rows,
            "active": sum(1 for row in rows if row["active"]),
            "total": len(rows),
            "backup": backup,
        }
        if record:
            history = _read(self.path, [])
            history = [item for item in history if isinstance(item, dict)]
            history.append({
                "at": report["checked_at"], "status": report["status"],
                "active": report["active"], "total": report["total"], "backup": backup,
            })
            _write(self.path, history[-MAX_HISTORY:])
        return report

    def dry_run(self) -> dict:
        results = []
        for job_id, unit, script in JOBS:
            path = self.root / script
            valid = False
            error = ""
            if path.exists():
                try:
                    py_compile.compile(str(path), doraise=True)
                    valid = True
                except Exception:
                    error = "compile_failed"
            else:
                error = "missing"
            results.append({"id": job_id, "script": script, "valid": valid, "error": error})
        return {"status": "ok" if all(item["valid"] for item in results) else "degraded", "jobs": results}
