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
SERVICE_MARKERS = (
    "голосовий виклик завершився", "голосовой вызов завершился",
    "відеовиклик завершився", "видеовызов завершился",
    "missed call", "входящий звонок", "исходящий звонок",
    "звонок завершен", "вызов завершен",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_utc(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_state(created_at: object) -> str:
    """Classify a local follow-up age without storing/revealing message data."""
    try:
        created = _as_utc(created_at)
        if created is None:
            return "unknown"
        hours = max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 3600)
    except Exception:
        return "unknown"
    if hours >= 24:
        return "overdue"
    if hours >= 1:
        return "attention"
    return "fresh"


def _classification(event: dict) -> str:
    """Classify transient notification text without storing it in lead data."""
    preview = " ".join(str(event.get(key) or "") for key in ("title", "text")).casefold().strip()
    if not preview:
        return "ignored_empty"
    if any(marker in preview for marker in SERVICE_MARKERS):
        return "ignored_service"
    return "message_candidate"


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
        self.tasks_path = self.root / "data" / "android_gateway" / "crm_followup_tasks.json"
        self.sync_state_path = self.root / "data" / "android_gateway" / "lead_sync_state.json"

    def _items(self) -> list[dict]:
        value = _read(self.path, [])
        return [item for item in value if isinstance(item, dict)]

    def _save(self, items: list[dict]) -> None:
        _write(self.path, items[-MAX_LEADS:])

    def _tasks(self) -> list[dict]:
        value = _read(self.tasks_path, [])
        return [item for item in value if isinstance(item, dict)]

    def _save_tasks(self, tasks: list[dict]) -> None:
        _write(self.tasks_path, tasks[-MAX_LEADS:])

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
        ignored = 0
        for event in notifications:
            if not isinstance(event, dict):
                continue
            package = str(event.get("package") or "")
            notification_id = str(event.get("id") or "")
            if package not in LEAD_SOURCES or not notification_id or notification_id in known:
                continue
            classification = _classification(event)
            is_candidate = classification == "message_candidate"
            items.append({
                "id": self._lead_id(package, notification_id),
                "notification_id": notification_id,
                "source": LEAD_SOURCES[package],
                "package": package,
                "observed_at": str(event.get("collected_at") or _now()),
                "status": "pending_review" if is_candidate else "ignored_notification",
                "classification": classification,
                "created_at": _now(),
                "requires_manual_chat_open": bool(is_candidate),
            })
            known.add(notification_id)
            if is_candidate:
                added += 1
            else:
                ignored += 1
        self._save(items)
        summary = self.summary()
        _write(self.sync_state_path, {"checked_at": _now(), "added": added, "ignored": ignored, "pending": summary.get("pending", 0)})
        return {"status": "ok", "added": added, "ignored": ignored, "total": summary.get("total", 0), "pending": summary.get("pending", 0)}

    def summary(self) -> dict:
        items = self._items()
        pending = [item for item in items if item.get("status") == "pending_review"]
        ignored = [item for item in items if item.get("status") == "ignored_notification"]
        by_source: dict[str, int] = {}
        for item in pending:
            source = str(item.get("source") or "Телефон")
            by_source[source] = by_source.get(source, 0) + 1
        tasks = self._tasks()
        open_tasks = [task for task in tasks if task.get("status") == "open"]
        age_states = [_age_state(task.get("created_at")) for task in open_tasks]
        return {
            "status": "ok", "total": len(items) - len(ignored), "pending": len(pending), "ignored": len(ignored), "by_source": by_source,
            "crm_open": len(open_tasks),
            "crm_attention": sum(state == "attention" for state in age_states),
            "crm_overdue": sum(state == "overdue" for state in age_states),
        }

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
            for item in rows[-max(1, min(int(limit), MAX_LEADS)):]
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

    def promote_to_crm_task(self, lead_id: str) -> dict:
        """Create a metadata-only CRM follow-up task, never a customer record."""
        items = self._items()
        tasks = self._tasks()
        target = str(lead_id or "")
        for task in tasks:
            if str(task.get("lead_id") or "") == target:
                return {"status": "already_promoted", "task_id": task.get("id"), "lead_id": target}
        for item in items:
            if str(item.get("id") or "") != target:
                continue
            if item.get("status") not in ("pending_review", "reviewed"):
                return {"status": "not_available", "lead_id": target}
            task_id = "crm-phone-" + hashlib.sha256((target + "|crm").encode("utf-8")).hexdigest()[:18]
            task = {
                "id": task_id,
                "lead_id": target,
                "source": str(item.get("source") or "Телефон"),
                "status": "open",
                "action": "review_messenger_contact",
                "created_at": _now(),
                "requires_manual_chat_open": True,
            }
            item["status"] = "crm_task_open"
            item["promoted_at"] = _now()
            tasks.append(task)
            self._save(items)
            self._save_tasks(tasks)
            return {"status": "crm_task_created", "task_id": task_id, "lead_id": target}
        return {"status": "not_found", "lead_id": target}

    def list_crm_tasks(self, limit: int = 50) -> list[dict]:
        rows = [task for task in self._tasks() if task.get("status") == "open"]
        return [
            {
                "id": task.get("id"), "lead_id": task.get("lead_id"),
                "source": task.get("source"), "created_at": task.get("created_at"),
                "action": task.get("action"), "status": task.get("status"),
                "age_state": _age_state(task.get("created_at")),
            }
            for task in rows[-max(1, min(int(limit), MAX_LEADS)):]
        ]

    def weekly_metrics(self, days: int = 7) -> dict:
        """Return counts for a period; never includes lead/customer content."""
        window = max(1, min(int(days), 90))
        cutoff = datetime.now(timezone.utc).timestamp() - window * 86400

        def recent(value: object) -> bool:
            parsed = _as_utc(value)
            return bool(parsed and parsed.timestamp() >= cutoff)

        leads = self._items()
        tasks = self._tasks()
        current = self.summary()
        return {
            "status": "ok",
            "days": window,
            "leads_created": sum(recent(item.get("created_at")) for item in leads),
            "leads_reviewed": sum(recent(item.get("reviewed_at")) for item in leads),
            "leads_promoted": sum(recent(item.get("promoted_at")) for item in leads),
            "tasks_created": sum(recent(task.get("created_at")) for task in tasks),
            "tasks_completed": sum(recent(task.get("completed_at")) for task in tasks),
            "tasks_open": int(current.get("crm_open") or 0),
            "tasks_attention": int(current.get("crm_attention") or 0),
            "tasks_overdue": int(current.get("crm_overdue") or 0),
        }

    def complete_crm_task(self, task_id: str) -> dict:
        tasks = self._tasks()
        target = str(task_id or "")
        for task in tasks:
            if str(task.get("id") or "") != target:
                continue
            if task.get("status") != "open":
                return {"status": "already_completed", "task_id": target}
            task["status"] = "done"
            task["completed_at"] = _now()
            self._save_tasks(tasks)
            return {"status": "completed", "task_id": target}
        return {"status": "not_found", "task_id": target}
