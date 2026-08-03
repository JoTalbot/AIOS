"""Privacy-preserving lead queue derived from Android messenger notifications.

The queue intentionally records *that* a potential customer contact occurred,
not its message, sender, phone number or notification preview.  Reviewing a
lead is a local task-state change only; CRM customer creation and messaging
remain separate explicitly confirmed actions.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEAD_SOURCES = {
    "com.whatsapp": "WhatsApp",
    "com.iMe.android": "iMe Messenger",
}
MAX_LEADS = 300


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


class AndroidLeadQueue:
    """Create generic review tasks from selected messenger notification IDs."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.notifications_path = self.root / "data" / "android_gateway" / "notifications.json"
        self.path = self.root / "data" / "android_gateway" / "lead_candidates.json"

    def _items(self) -> list[dict]:
        value = _read(self.path, [])
        return [item for item in value if isinstance(item, dict)]

    def _save(self, items: list[dict]) -> None:
        _write(self.path, items[-MAX_LEADS:])

    @staticmethod
    def _lead_id(package: str, notification_id: str) -> str:
        raw = f"{package}|{notification_id}".encode("utf-8")
        return "phone-" + hashlib.sha256(raw).hexdigest()[:18]

    def sync(self) -> dict:
        """Import only event identity/source/timestamps, never notification text."""
        notifications = _read(self.notifications_path, [])
        items = self._items()
        known = {str(item.get("notification_id") or "") for item in items}
        added = 0
        for event in notifications:
            if not isinstance(event, dict):
                continue
            package = str(event.get("package") or "")
            notification_id = str(event.get("id") or "")
            if package not in LEAD_SOURCES or not notification_id or notification_id in known:
                continue
            items.append({
                "id": self._lead_id(package, notification_id),
                "notification_id": notification_id,
                "source": LEAD_SOURCES[package],
                "package": package,
                "observed_at": str(event.get("collected_at") or _now()),
                "status": "pending_review",
                "created_at": _now(),
                "requires_manual_chat_open": True,
            })
            known.add(notification_id)
            added += 1
        self._save(items)
        return {"status": "ok", "added": added, "total": len(items), "pending": self.summary().get("pending", 0)}

    def summary(self) -> dict:
        items = self._items()
        pending = [item for item in items if item.get("status") == "pending_review"]
        by_source: dict[str, int] = {}
        for item in pending:
            source = str(item.get("source") or "Телефон")
            by_source[source] = by_source.get(source, 0) + 1
        return {"status": "ok", "total": len(items), "pending": len(pending), "by_source": by_source}

    def list_pending(self, limit: int = 20, source: str = "") -> list[dict]:
        source_key = str(source or "").casefold()
        rows = [item for item in self._items() if item.get("status") == "pending_review"]
        if source_key:
            rows = [item for item in rows if source_key in str(item.get("source") or "").casefold()]
        # Do not return notification title/text: they are not part of this queue.
        return [
            {
                "id": item.get("id"), "source": item.get("source"),
                "observed_at": item.get("observed_at"), "status": item.get("status"),
                "requires_manual_chat_open": bool(item.get("requires_manual_chat_open")),
            }
            for item in rows[-max(1, min(int(limit), 50)):]
        ]

    def review(self, lead_id: str) -> dict:
        items = self._items()
        target = str(lead_id or "")
        for item in items:
            if str(item.get("id") or "") != target:
                continue
            if item.get("status") != "pending_review":
                return {"status": "already_reviewed", "id": target}
            item["status"] = "reviewed"
            item["reviewed_at"] = _now()
            self._save(items)
            return {"status": "reviewed", "id": target}
        return {"status": "not_found", "id": target}
