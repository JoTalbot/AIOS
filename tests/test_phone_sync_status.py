"""Phone sync freshness (metadata-only) — unit tests for PhoneSyncStatus and its runner.

Покрывает run_phone_sync_status.py и aios_core/phone_sync_status.py.
Никогда не читает содержимое уведомлений — только метаданные и время.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def _write(tmp_path, name: str, payload: dict, mtime: datetime | None = None):
    path = tmp_path / "data" / "android_gateway" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    if mtime is not None:
        import os

        os.utime(path, (mtime.timestamp(), mtime.timestamp()))
    return path


def _status(tmp_path):
    import aios_core.phone_sync_status as m

    return m.PhoneSyncStatus(tmp_path).snapshot()


def test_snapshot_empty_dir_shape():
    """Пустая директория: status ok, все источники missing, fresh=0."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        snap = _status(d)
        assert snap["status"] == "ok"
        assert snap["total"] == 7  # количество SOURCES
        assert snap["fresh"] == 0
        assert len(snap["sources"]) == 7
        for row in snap["sources"]:
            assert row["exists"] is False
            assert row["status"] == "missing"


def test_snapshot_fresh_file(tmp_path):
    """Свежий файл (checked_at только что) учитывается в fresh и отдаёт статус."""
    now = datetime.now(timezone.utc)
    _write(
        tmp_path,
        "notification_alerts_state.json",
        {"checked_at": now.isoformat(), "status": "ok"},
    )
    snap = _status(tmp_path)
    by_id = {r["id"]: r for r in snap["sources"]}
    row = by_id["notifications"]
    assert row["exists"] is True
    assert row["status"] == "ok"
    assert row["age_minutes"] == 0
    assert snap["fresh"] == 1


def test_snapshot_stale_mtime_not_fresh(tmp_path):
    """Файл старше 24ч по mtime существует, но не считается свежим."""
    old = datetime.now(timezone.utc) - timedelta(days=3)
    _write(tmp_path, "lead_sync_state.json", {"action": "synced"}, mtime=old)
    snap = _status(tmp_path)
    row = next(r for r in snap["sources"] if r["id"] == "lead_sync")
    assert row["exists"] is True
    assert row["status"] == "synced"
    assert row["age_minutes"] is not None and row["age_minutes"] > 24 * 60
    assert snap["fresh"] == 0


def test_snapshot_broken_json_treated_as_empty(tmp_path):
    """Битый JSON не роняет snapshot — payload считается пустым."""
    path = tmp_path / "data" / "android_gateway" / "recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    snap = _status(tmp_path)
    row = next(r for r in snap["sources"] if r["id"] == "recovery")
    assert row["exists"] is True
    assert row["status"] == "missing"
    assert snap["status"] == "ok"


def test_age_minutes_missing_file_returns_none(tmp_path):
    """age для несуществующего файла — None (OSError перехвачен)."""
    import aios_core.phone_sync_status as m

    missing = tmp_path / "data" / "android_gateway" / "nope.json"
    assert m._age_minutes(missing, {}) is None


def test_payload_secrets_never_surfaced(tmp_path):
    """Metadata-only: содержимое payload (в т.ч. секреты) не попадает в отчёт."""
    now = datetime.now(timezone.utc)
    _write(
        tmp_path,
        "lead_sync_state.json",
        {"checked_at": now.isoformat(), "status": "ok", "secret": "super-secret-token", "session_key": "k"},
    )
    snap = _status(tmp_path)
    assert "super-secret-token" not in str(snap)
    assert "session_key" not in str(snap)
    # в отчёт попадает только id/exists/age_minutes/status
    row = next(r for r in snap["sources"] if r["id"] == "lead_sync")
    assert set(row.keys()) == {"id", "exists", "age_minutes", "status"}


def test_runner_import_and_snapshot_callable():
    """Раннер run_phone_sync_status импортируется и вызывает snapshot."""
    import run_phone_sync_status as runner  # noqa: F401

    import aios_core.phone_sync_status as m

    # Раннер в __main__ выводит json.dumps(snapshot()) — проверим, что это валидный JSON на tmp-директории
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        snap = m.PhoneSyncStatus(d).snapshot()
        dumped = json.dumps(snap, ensure_ascii=False, indent=2)
        assert json.loads(dumped)["status"] == "ok"
