"""Freshness/status of metadata-only phone synchronization jobs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SOURCES = {
    "notifications": "notification_alerts_state.json",
    "lead_sync": "lead_sync_state.json",
    "bank_sync": "bank_monitor_state.json",
    "lead_digest": "lead_digest_state.json",
    "daily_digest": "phone_control_digest_state.json",
    "weekly_report": "phone_weekly_report_state.json",
    "recovery": "recovery.json",
}


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _age_minutes(path: Path, payload: dict) -> int | None:
    raw = payload.get("checked_at") or payload.get("sent_at") or payload.get("bootstrapped_at")
    try:
        if raw:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(0, int((datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() / 60))
    except Exception:
        pass
    try:
        return max(0, int((datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 60))
    except OSError:
        return None


class PhoneSyncStatus:
    """Read synchronization freshness only; never accesses notification payloads."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.data = self.root / "data" / "android_gateway"

    def snapshot(self) -> dict:
        rows = []
        for key, name in SOURCES.items():
            path = self.data / name
            payload = _read(path)
            rows.append({
                "id": key,
                "exists": path.exists(),
                "age_minutes": _age_minutes(path, payload),
                "status": str(payload.get("status") or payload.get("action") or "ok") if payload else "missing",
            })
        fresh = sum(row["exists"] and (row["age_minutes"] is None or row["age_minutes"] <= 24 * 60) for row in rows)
        return {"status": "ok", "sources": rows, "fresh": fresh, "total": len(rows)}
