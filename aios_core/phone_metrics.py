"""Metadata-only historical metrics for AIOS phone operations."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

MAX_SNAPSHOTS = 180


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


class PhoneMetricsStore:
    """Store only aggregate booleans/counts, never phone or message content."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "data" / "android_gateway" / "control_history.json"

    def _rows(self) -> list[dict]:
        value = _read(self.path, [])
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _row(snapshot: dict) -> dict:
        device = snapshot.get("device") or {}
        leads = snapshot.get("leads") or {}
        bank_tasks = snapshot.get("bank_tasks") or {}
        templates = snapshot.get("templates") or {}
        audit = snapshot.get("audit") or {}
        apps = snapshot.get("apps") or []
        banks = snapshot.get("banks") or []
        timers = snapshot.get("timers") or {}
        by_source = leads.get("by_source") or {}
        return {
            "at": _now(),
            "adb_connected": bool(device.get("connected")),
            "companion_connected": bool(device.get("companion")),
            "location_ready": bool(device.get("location_ready")),
            "camera_permission": bool(device.get("camera_permission")),
            "microphone_permission": bool(device.get("microphone_permission")),
            "apps_available": sum(1 for app in apps if app.get("available")),
            "apps_calibrated": sum(1 for app in apps if app.get("calibrated")),
            "leads_pending": int(leads.get("pending") or 0),
            "leads_whatsapp": int(by_source.get("WhatsApp") or 0),
            "leads_ime": int(by_source.get("iMe Messenger") or 0),
            "crm_open": int(leads.get("crm_open") or 0),
            "crm_attention": int(leads.get("crm_attention") or 0),
            "crm_overdue": int(leads.get("crm_overdue") or 0),
            "bank_unread": sum(int(bank.get("unread_notifications") or 0) for bank in banks),
            "bank_tasks": int(bank_tasks.get("pending") or 0),
            "bank_attention": int(bank_tasks.get("attention") or 0),
            "bank_overdue": int(bank_tasks.get("overdue") or 0),
            "templates_count": int(templates.get("count") or 0),
            "templates_stale": int(templates.get("stale") or 0),
            "audit_count": int(audit.get("count") or 0),
            "timers_active": sum(1 for active in timers.values() if active),
            "timers_total": len(timers),
        }

    def record(self, snapshot: dict) -> dict:
        rows = self._rows()
        row = self._row(snapshot)
        rows.append(row)
        _write(self.path, rows[-MAX_SNAPSHOTS:])
        return row

    def recent(self, limit: int = 30) -> list[dict]:
        return self._rows()[-max(1, min(int(limit), MAX_SNAPSHOTS)):]

    def trend(self, limit: int = 7) -> dict:
        rows = self.recent(limit)
        if not rows:
            return {"status": "ok", "snapshots": 0, "changes": {}}
        first, last = rows[0], rows[-1]
        fields = (
            "leads_pending", "crm_open", "crm_attention", "crm_overdue", "bank_unread", "bank_tasks", "bank_attention", "bank_overdue",
            "adb_connected", "companion_connected", "location_ready", "camera_permission", "microphone_permission",
            "apps_available", "apps_calibrated", "timers_active",
        )
        return {
            "status": "ok", "snapshots": len(rows),
            "changes": {field: int(bool(last.get(field))) - int(bool(first.get(field))) if isinstance(last.get(field), bool) else int(last.get(field) or 0) - int(first.get(field) or 0) for field in fields},
            "last": last,
        }

    def availability(self, limit: int = 30) -> dict:
        rows = self.recent(limit)
        if not rows:
            return {"status": "ok", "snapshots": 0, "adb_pct": 0, "companion_pct": 0, "location_pct": 0, "timers_pct": 0}
        total = len(rows)
        pct = lambda key: round(100 * sum(bool(row.get(key)) for row in rows) / total)
        timers_ok = sum(bool(row.get("timers_total")) and int(row.get("timers_active") or 0) == int(row.get("timers_total") or 0) for row in rows)
        return {
            "status": "ok", "snapshots": total,
            "adb_pct": pct("adb_connected"), "companion_pct": pct("companion_connected"),
            "location_pct": pct("location_ready"), "camera_pct": pct("camera_permission"),
            "microphone_pct": pct("microphone_permission"), "timers_pct": round(100 * timers_ok / total),
        }

    def calibration_report(self) -> dict:
        value = _read(self.root / "data" / "android_gateway" / "app_ui_calibrations.json", {})
        rows = []
        for profile, item in (value.items() if isinstance(value, dict) else []):
            if not isinstance(item, dict):
                continue
            selectors = dict(item.get("selectors") or {})
            rows.append({
                "profile": str(profile), "checked_at": str(item.get("checked_at") or ""),
                "ready": bool(selectors) and all(bool(value) for value in selectors.values()),
                "selectors": len(selectors),
            })
        return {"status": "ok", "count": len(rows), "apps": rows}

    def export_csv(self) -> Path:
        rows = self._rows()
        target = self.root / "data" / "exports" / f"phone_metrics_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        fields = list(self._row({}).keys())
        with target.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return target
