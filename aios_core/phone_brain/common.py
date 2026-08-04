"""Общие утилиты Phone Brain: UTC-время и атомарный JSON.

Единственное каноническое место этих хелперов внутри phone_brain —
никаких копий _read/_write/_now в каждом модуле.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    """Текущее время в UTC (aware)."""
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    """ISO-строка с точностью до секунды; сравнима лексикографически."""
    return (value or utc_now()).isoformat(timespec="seconds")


def parse_iso(value: object) -> datetime | None:
    """Безопасный разбор ISO-строки обратно в datetime."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def read_json(path: Path, default: Any) -> Any:
    """Читает JSON-файл; при любой ошибке возвращает default нужного типа."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    """Атомарно пишет JSON (tmp + os.replace), права по умолчанию 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)
    try:
        path.chmod(mode)
    except OSError:
        pass
