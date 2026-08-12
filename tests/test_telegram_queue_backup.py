from __future__ import annotations

import sqlite3
import threading
import time

import pytest
from cryptography.fernet import Fernet

from scripts.telegram_queue_backup import (
    create_backup,
    restore_drill,
    restore_to,
    verify_backup,
)
from tg_bot.crypto_store import QueueCipher


def _queue_db(path, table: str, cipher: QueueCipher) -> None:
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, text TEXT, encrypted INTEGER, status TEXT)"
        )
        db.execute(
            f"INSERT INTO {table} VALUES (1, ?, 1, 'pending')",
            (cipher.encrypt("private queue payload"),),
        )


def test_wal_safe_backup_key_escrow_and_restore_drill(tmp_path):
    data = tmp_path / "data"
    backups = tmp_path / "backups"
    keys = tmp_path / "key-escrow"
    data.mkdir()
    key = tmp_path / "queue.key"
    key.write_bytes(Fernet.generate_key() + b"\n")
    cipher = QueueCipher(key)
    _queue_db(data / "telegram_outbox.sqlite3", "telegram_outbox", cipher)
    _queue_db(data / "telegram_generation.sqlite3", "telegram_generation", cipher)

    # Keep a WAL connection active while sqlite3.Connection.backup() runs.
    writer_done = threading.Event()

    def writer() -> None:
        with sqlite3.connect(data / "telegram_generation.sqlite3") as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "INSERT INTO telegram_generation VALUES (2, ?, 1, 'pending')",
                (cipher.encrypt("concurrent"),),
            )
            db.commit()
        writer_done.set()

    thread = threading.Thread(target=writer)
    thread.start()
    backup = create_backup(
        data_dir=data,
        backup_root=backups,
        key_file=key,
        key_backup_root=keys,
        timestamp="20260812T010000Z",
    )
    thread.join(2)
    assert writer_done.is_set()

    result = verify_backup(backup, keys)
    assert result["databases"] == 2
    assert restore_drill(backup, keys)["databases"] == 2
    assert not any(backups.rglob("*.key"))
    assert next(keys.glob("*.key")).stat().st_mode & 0o777 == 0o600

    restored = tmp_path / "restored"
    restore_to(backup, keys, restored)
    with sqlite3.connect(restored / "telegram_outbox.sqlite3") as db:
        value = db.execute("SELECT text FROM telegram_outbox").fetchone()[0]
    assert cipher.decrypt(value) == "private queue payload"


def test_restore_drill_rejects_corrupted_backup(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    key = tmp_path / "queue.key"
    key.write_bytes(Fernet.generate_key() + b"\n")
    _queue_db(data / "telegram_outbox.sqlite3", "telegram_outbox", QueueCipher(key))
    backup = create_backup(
        data_dir=data,
        backup_root=tmp_path / "backups",
        key_file=key,
        key_backup_root=tmp_path / "keys",
        timestamp="20260812T020000Z",
    )
    with (backup / "telegram_outbox.sqlite3").open("r+b") as handle:
        handle.seek(100)
        handle.write(b"CORRUPT")
    with pytest.raises(RuntimeError, match="checksum"):
        verify_backup(backup, tmp_path / "keys")
