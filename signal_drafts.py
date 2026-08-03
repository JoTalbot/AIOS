"""Очередь черновиков ответов Signal с явным подтверждением владельца.

Фоновый Signal-обработчик может сгенерировать текст, но не отправляет его сам в
режиме ``auto_send=false``. Черновик сохраняется здесь, а Telegram-бот получает
кнопки «Отправить» / «Отклонить».
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SignalDraftStore:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root is not None else PROJECT_ROOT
        self.path = self.root / "data" / "signal_pending_replies.json"
        self.lock_path = self.root / "data" / ".signal_pending_replies.lock"

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            try:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
            try:
                yield
            finally:
                try:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass

    def _load(self) -> list[dict]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except Exception:
            return []

    def _save(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(rows[-300:], ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _source_hash(contact: str, source_text: str) -> str:
        return hashlib.sha256(f"{contact}\0{source_text}".encode("utf-8")).hexdigest()[:20]

    def enqueue(self, contact: str, text: str, source_text: str = "") -> tuple[dict, bool]:
        """Добавить черновик. Возвращает ``(draft, created)`` без дубликатов."""
        contact = str(contact or "").strip()
        text = str(text or "").strip()
        if not contact or not text:
            raise ValueError("Нужны contact и text")
        source_hash = self._source_hash(contact, source_text or text)
        draft_id = "vbr_" + source_hash[:12]
        with self._lock():
            rows = self._load()
            for row in rows:
                if row.get("source_hash") == source_hash and row.get("contact") == contact:
                    return row, False
            draft = {
                "id": draft_id,
                "contact": contact,
                "text": text[:3500],
                "source_hash": source_hash,
                "status": "pending",
                "created_at": _now(),
                "updated_at": _now(),
            }
            rows.append(draft)
            self._save(rows)
            return draft, True

    def claim(self, draft_id: str) -> dict | None:
        """Атомарно взять pending-черновик на отправку."""
        with self._lock():
            rows = self._load()
            for row in rows:
                if row.get("id") == draft_id:
                    if row.get("status") != "pending":
                        return None
                    row.update({"status": "sending", "updated_at": _now()})
                    self._save(rows)
                    return dict(row)
        return None

    def cancel(self, draft_id: str) -> dict | None:
        with self._lock():
            rows = self._load()
            for row in rows:
                if row.get("id") == draft_id:
                    if row.get("status") != "pending":
                        return None
                    row.update({"status": "cancelled", "updated_at": _now(), "cancelled_at": _now()})
                    self._save(rows)
                    return dict(row)
        return None

    def finalize(self, draft_id: str, sent: bool, error: str = "") -> dict | None:
        with self._lock():
            rows = self._load()
            for row in rows:
                if row.get("id") == draft_id:
                    row.update({
                        "status": "sent" if sent else "pending",
                        "updated_at": _now(),
                        "sent_at": _now() if sent else "",
                        "last_error": str(error or "")[:300],
                    })
                    self._save(rows)
                    return dict(row)
        return None

    def pending(self, limit: int = 20) -> list[dict]:
        return [row for row in self._load() if row.get("status") == "pending"][-limit:]
