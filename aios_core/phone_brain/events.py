"""Журнал событий Phone Brain (JSONL) — фундамент будущего reaction engine.

Пишутся только метаданные событий (тип, время, технический payload), без
содержимого экрана, чатов и уведомлений — в духе существующей политики приватности.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aios_core.phone_brain.common import iso

MAX_BYTES = 512 * 1024


class EventLog:
    """Append-only журнал событий с простой ротацией по размеру."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def append(self, event_type: str, data: dict | None = None) -> dict:
        """Добавляет событие {at, type, data}."""
        event = {"at": iso(), "type": str(event_type or "unknown")[:80],
                 "data": data if isinstance(data, dict) else {}}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size > MAX_BYTES:
                rotated = self.path.with_suffix(".old")
                try:
                    os.replace(self.path, rotated)
                except OSError:
                    pass
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return event

    def recent(self, limit: int = 50) -> list[dict]:
        """Последние N событий (для CLI/API/диагностики)."""
        limit = max(1, min(int(limit), 500))
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        except Exception:
            return []
        events: list[dict] = []
        for line in lines:
            try:
                item: Any = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                events.append(item)
        return events
