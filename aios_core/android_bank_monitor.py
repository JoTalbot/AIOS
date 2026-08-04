"""Read-only bank app availability and notification metadata monitor."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .android_gateway import AndroidGateway


BANKS = {
    "abank": {"title": "A-Bank", "package": "ua.com.abank"},
    "privat24": {"title": "Privat24", "package": "ua.privatbank.ap24"},
}
MAX_TASKS = 300


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
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class AndroidBankMonitor:
    """Return only app availability/counts and metadata-only follow-up tasks."""

    def __init__(self, root: Path | str, gateway_factory: Callable[[Path], AndroidGateway] = AndroidGateway):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        data = self.root / "data" / "android_gateway"
        self.notifications_path = data / "notifications.json"
        self.tasks_path = data / "bank_notification_tasks.json"
        self.state_path = data / "bank_monitor_state.json"

    def _events(self) -> list[dict]:
        value = _read(self.notifications_path, [])
        return [item for item in value if isinstance(item, dict)]

    def _tasks(self) -> list[dict]:
        value = _read(self.tasks_path, [])
        return [item for item in value if isinstance(item, dict)]

    def _save_tasks(self, tasks: list[dict]) -> None:
        _write(self.tasks_path, tasks[-MAX_TASKS:])

    @staticmethod
    def _task_id(package: str, event_id: str) -> str:
        return "bank-" + hashlib.sha256(f"{package}|{event_id}".encode("utf-8")).hexdigest()[:18]

    def bootstrap(self) -> dict:
        """Mark existing bank events as known without creating retrospective tasks."""
        known = [str(event.get("id") or "") for event in self._events() if event.get("package") in {bank["package"] for bank in BANKS.values()} and event.get("id")]
        _write(self.state_path, {"known_ids": known[-600:], "bootstrapped_at": _now()})
        return {"status": "ok", "known": len(known)}

    def sync_tasks(self) -> dict:
        state = _read(self.state_path, {"known_ids": []})
        known = {str(value) for value in (state.get("known_ids") or [])}
        tasks = self._tasks()
        existing_ids = {str(task.get("notification_id") or "") for task in tasks}
        added = 0
        bank_by_package = {bank["package"]: bank for bank in BANKS.values()}
        for event in self._events():
            package = str(event.get("package") or "")
            event_id = str(event.get("id") or "")
            if package not in bank_by_package or not event_id or event_id in known or event_id in existing_ids:
                continue
            bank = bank_by_package[package]
            tasks.append({
                "id": self._task_id(package, event_id),
                "notification_id": event_id,
                "source": bank["title"],
                "package": package,
                "observed_at": str(event.get("collected_at") or _now()),
                "status": "pending_review",
                "created_at": _now(),
                "action": "review_bank_notification_manually",
            })
            known.add(event_id)
            added += 1
        self._save_tasks(tasks)
        _write(self.state_path, {"known_ids": list(known)[-600:], "checked_at": _now()})
        return {"status": "ok", "added": added, "pending": self.task_summary().get("pending", 0)}

    def task_summary(self) -> dict:
        tasks = self._tasks()
        pending = [task for task in tasks if task.get("status") == "pending_review"]
        by_source: dict[str, int] = {}
        for task in pending:
            source = str(task.get("source") or "Банк")
            by_source[source] = by_source.get(source, 0) + 1
        return {"status": "ok", "total": len(tasks), "pending": len(pending), "by_source": by_source}

    def list_tasks(self, limit: int = 30) -> list[dict]:
        return [
            {"id": task.get("id"), "source": task.get("source"), "observed_at": task.get("observed_at"), "status": task.get("status")}
            for task in self._tasks() if task.get("status") == "pending_review"
        ][-max(1, min(int(limit), MAX_TASKS)):]

    def review_task(self, task_id: str) -> dict:
        target = str(task_id or "")
        tasks = self._tasks()
        for task in tasks:
            if str(task.get("id") or "") != target:
                continue
            if task.get("status") != "pending_review":
                return {"status": "already_reviewed", "id": target}
            task["status"] = "reviewed"
            task["reviewed_at"] = _now()
            self._save_tasks(tasks)
            return {"status": "reviewed", "id": target}
        return {"status": "not_found", "id": target}

    def snapshot(self) -> dict:
        gateway = self.gateway_factory(self.root)
        profiles = {str(item.get("id")): item for item in (gateway.app_profiles().get("profiles") or [])}
        events = self._events()
        rows = []
        for key, bank in BANKS.items():
            profile = profiles.get(key) or {}
            package = bank["package"]
            unread = sum(1 for event in events if event.get("package") == package and not event.get("read"))
            rows.append({
                "id": key,
                "title": bank["title"],
                "available": bool(profile.get("available")),
                "unread_notifications": unread,
                "mode": "только уведомления и подтверждаемое открытие",
            })
        return {"status": "ok", "banks": rows, "tasks": self.task_summary()}


def format_telegram(snapshot: dict) -> str:
    lines = ["🏦 <b>БАНКИ НА ТЕЛЕФОНЕ · БЕЗОПАСНЫЙ РЕЖИМ</b>", "━━━━━━━━━━━━━━━━"]
    for bank in snapshot.get("banks") or []:
        state = "✅ доступно" if bank.get("available") else "➕ не установлено"
        lines.append(f"• <b>{bank.get('title')}</b>: {state} · уведомлений: {bank.get('unread_notifications', 0)}")
    tasks = snapshot.get("tasks") or {}
    lines.append(f"Локальных задач на проверку: {tasks.get('pending', 0)}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Баланс, карты, OTP, переводы, платежи и биометрия не читаются и не выполняются.</i>")
    return "\n".join(lines)
