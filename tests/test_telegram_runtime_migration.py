from __future__ import annotations

from scripts.migrate_telegram_runtime import main


def test_runtime_migration_verifies_and_removes_only_telegram_files(tmp_path, monkeypatch):
    source_state = tmp_path / "repo-data"
    source_logs = tmp_path / "repo-logs"
    source_backup = tmp_path / "repo-backups"
    source_keys = tmp_path / "repo-key-backups"
    for path in (source_state, source_logs, source_backup / "stamp", source_keys):
        path.mkdir(parents=True)
    (source_state / "telegram_outbox.sqlite3").write_bytes(b"queue")
    (source_state / "unrelated-user-audio.wav").write_bytes(b"keep")
    (source_logs / "tg.log").write_text("redacted log", encoding="utf-8")
    (source_backup / "stamp" / "manifest.json").write_text("{}", encoding="utf-8")
    (source_keys / "stamp.key").write_text("escrow", encoding="utf-8")

    destination = tmp_path / "runtime"
    argv = [
        "migrate",
        "--source-state", str(source_state),
        "--source-logs", str(source_logs),
        "--source-backups", str(source_backup),
        "--source-key-backups", str(source_keys),
        "--state", str(destination / "state"),
        "--logs", str(destination / "logs"),
        "--backups", str(destination / "backups"),
        "--key-backups", str(destination / "keys"),
        "--remove-source",
    ]
    monkeypatch.setattr("sys.argv", argv)
    assert main() == 0
    assert (destination / "state" / "telegram_outbox.sqlite3").read_bytes() == b"queue"
    assert (destination / "logs" / "tg.log").read_text() == "redacted log"
    assert (destination / "backups" / "stamp" / "manifest.json").is_file()
    assert (destination / "keys" / "stamp.key").is_file()
    assert not (source_state / "telegram_outbox.sqlite3").exists()
    assert (source_state / "unrelated-user-audio.wav").read_bytes() == b"keep"
