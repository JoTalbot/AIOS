"""Тесты локального защищённого бэкапа профилей мессенджеров."""
from __future__ import annotations

import tarfile
from pathlib import Path


def test_backup_profiles_excludes_caches_and_sets_permissions(tmp_path):
    import run_messenger_profile_backup as backup

    signal = tmp_path / "Signal"
    viber = tmp_path / "Viber"
    (signal / "sql").mkdir(parents=True)
    (signal / "Cache").mkdir()
    viber.mkdir()
    (signal / "sql" / "db.sqlite").write_text("state", encoding="utf-8")
    (signal / "Cache" / "blob").write_text("cache", encoding="utf-8")
    (viber / "session.json").write_text("session", encoding="utf-8")

    result = backup.backup({"signal": signal, "viber": viber}, tmp_path / "backups", retention=2)
    assert result["status"] == "ok"
    archive = Path(result["backup"]) / "profiles.tar.gz"
    assert archive.exists()
    assert archive.stat().st_mode & 0o777 == 0o600
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert "signal/sql/db.sqlite" in names
    assert not any("Cache" in name for name in names)


def test_backup_retention_removes_old_directories(tmp_path):
    import run_messenger_profile_backup as backup

    profile = tmp_path / "Signal"
    profile.mkdir()
    (profile / "state").write_text("x", encoding="utf-8")
    root = tmp_path / "backups"
    backup.backup({"signal": profile}, root, retention=1)
    backup.backup({"signal": profile}, root, retention=1)
    assert len([p for p in root.iterdir() if p.is_dir()]) == 1
