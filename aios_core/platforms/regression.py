"""Regression — контроль дрейфа маркеров верстки платформы.

Приложения обновляются, resource-id меняются — парсер молча начинает
собирать ноль карточек. MarkerDrift сравнивает baseline
(``extras.parser_hints`` дескриптора) со свежей калибровкой дампа и
честно отвечает ``ok`` / ``drift`` / ``no-baseline``: по ``drift``
запускается ``codegen --force`` для перекомпиляции парсера.

CLI: ``aios platforms marker-check --platform X --dump new_feed.xml``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

from .calibrate import CalibrationAdvisor
from .parsergen import extract_markers

_DRIFT_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_drift_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    platform TEXT NOT NULL,
    removed INTEGER NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_drift_platform
    ON platform_drift_events(platform);
"""

DEFAULT_DRIFT_DB = "data/marker-drift.sqlite"


def _drift_conn(db_path: Union[str, Path]) -> sqlite3.Connection:
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_DRIFT_SCHEMA)
    return conn


def _record_drift_event(
    db_path: Union[str, Path],
    platform: str,
    *,
    removed: int,
    detail: str = "",
) -> int:
    """Персистит drift-событие (возвращает id строки)."""
    at = datetime.now(timezone.utc).isoformat()
    conn = _drift_conn(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO platform_drift_events "
                "(at, platform, removed, detail) VALUES (?, ?, ?, ?)",
                (at, platform, removed, detail),
            )
            return int(cursor.lastrowid)
    finally:
        conn.close()


def drift_events_summary(
    db_path: Union[str, Path] = DEFAULT_DRIFT_DB,
) -> Dict[str, int]:
    """Количество drift-событий по платформам ({} если базы нет)."""
    if str(db_path) != ":memory:" and not Path(db_path).exists():
        return {}
    conn = _drift_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT platform, COUNT(*) FROM platform_drift_events "
            "GROUP BY platform ORDER BY platform"
        ).fetchall()
        return {str(platform): int(count) for platform, count in rows}
    finally:
        conn.close()


def diff_markers(
    old_hints: Dict, new_hints: Dict
) -> Dict[str, List[str]]:
    """Сравнивает card-маркеры двух parser_hints.

    Returns:
        {removed, added, kept} — списки substring-маркеров.
    """
    old = set(extract_markers(old_hints))
    new = set(extract_markers(new_hints))
    return {
        "removed": sorted(old - new),
        "added": sorted(new - old),
        "kept": sorted(old & new),
    }


def check_platform_markers(
    platform_name: str,
    xml_source: Union[str, Path],
    directory="platforms",
    drift_db: Optional[Union[str, Path]] = None,
) -> Dict[str, object]:
    """Проверяет дрейф маркеров платформы по свежему дампу выдачи.

    Args:
        platform_name: Имя платформы (дескриптор в ``directory``).
        xml_source: Свежий UI-дамп поисковой выдачи.
        directory: Каталог YAML-каталога платформ.
        drift_db: Необязательный путь к sqlite-базе — события `drift`
            персистятся (таблица ``platform_drift_events``), чтобы
            телеметрия отдавала их как ``aios_marker_drift_events``.

    Returns:
        {platform, status, diff, baseline_markers, fresh_markers};
        status: ``ok`` (baseline жив), ``drift`` (baseline-маркеры
        потеряны → re-calibrate + codegen --force), ``no-baseline``
        (дескриптор без parser_hints).

    Raises:
        ValueError: Дескриптор платформы не найден.
    """
    yaml_path = Path(directory) / f"{platform_name}.yaml"
    if not yaml_path.exists():
        raise ValueError(f"descriptor not found: {yaml_path}")
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    baseline = (doc.get("extras") or {}).get("parser_hints") or {}
    if not extract_markers(baseline):
        return {
            "platform": platform_name,
            "status": "no-baseline",
            "hint": "run aios platforms calibrate --write first",
            "baseline_markers": [],
            "fresh_markers": [],
            "diff": {"removed": [], "added": [], "kept": []},
        }
    fresh = CalibrationAdvisor().analyze(xml_source)
    diff = diff_markers(baseline, fresh)
    status = "drift" if diff["removed"] else "ok"
    if status == "drift" and drift_db is not None:
        _record_drift_event(
            drift_db, platform_name,
            removed=len(diff["removed"]),
            detail=str(diff["removed"])[:200],
        )
    return {
        "platform": platform_name,
        "status": status,
        "hint": (
            "baseline markers lost — recalibrate: "
            "calibrate --write && codegen --force"
            if diff["removed"] else "baseline markers intact"
        ),
        "baseline_markers": sorted(extract_markers(baseline)),
        "fresh_markers": sorted(extract_markers(fresh)),
        "diff": diff,
    }
