"""Metadata-only audit trail for confirmed Android workflow actions.

This log is deliberately not a screen recorder. It never stores messages,
chat/contact names, clipboard content, GPS coordinates, screenshots, audio,
file names or tap coordinates.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_EVENTS = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class PhoneActionAudit:
    """Append bounded, non-sensitive phone workflow telemetry."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "data" / "android_gateway" / "action_audit.json"

    def record(self, action: str, status: str, package: str = "") -> dict:
        events = _read(self.path, [])
        if not isinstance(events, list):
            events = []
        event = {
            "at": _now(),
            "action": str(action or "unknown")[:80],
            "status": str(status or "unknown")[:40],
        }
        if package:
            event["package"] = str(package)[:120]
        events.append(event)
        _write(self.path, events[-MAX_EVENTS:])
        return event

    def recent(self, limit: int = 20) -> list[dict]:
        events = _read(self.path, [])
        if not isinstance(events, list):
            return []
        return [
            {
                "at": str(event.get("at") or ""),
                "action": str(event.get("action") or "unknown"),
                "status": str(event.get("status") or "unknown"),
                "package": str(event.get("package") or ""),
            }
            for event in events[-max(1, min(int(limit), 100)):]
            if isinstance(event, dict)
        ]

    def summary(self) -> dict:
        events = self.recent(limit=MAX_EVENTS)
        return {"status": "ok", "count": len(events), "last": events[-1] if events else None}
