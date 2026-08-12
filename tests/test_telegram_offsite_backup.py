from __future__ import annotations

import base64
import json
import os
import tarfile
from pathlib import Path

from scripts.telegram_offsite_backup import (
    create_encrypted_bundle,
    decrypt_file,
    encrypt_file,
)


def test_streaming_aes_gcm_round_trip_rejects_tampering(tmp_path):
    key = os.urandom(32)
    source = tmp_path / "source"
    source.write_bytes(os.urandom(2 * 1024 * 1024 + 17))
    encrypted = tmp_path / "encrypted"
    restored = tmp_path / "restored"
    encrypt_file(source, encrypted, key)
    decrypt_file(encrypted, restored, key)
    assert restored.read_bytes() == source.read_bytes()

    value = bytearray(encrypted.read_bytes())
    value[len(value) // 2] ^= 1
    encrypted.write_bytes(value)
    try:
        decrypt_file(encrypted, tmp_path / "tampered", key)
    except Exception:
        pass
    else:
        raise AssertionError("AES-GCM authentication must reject tampering")


def test_bundle_contains_backup_and_matching_key_only_inside_encryption(tmp_path):
    backup = tmp_path / "backups" / "20260812T120000Z"
    backup.mkdir(parents=True)
    (backup / "telegram_outbox.sqlite3").write_bytes(b"encrypted queue")
    key_root = tmp_path / "keys"
    key_root.mkdir()
    queue_key = key_root / "20260812T120000Z.key"
    queue_key.write_text(base64.urlsafe_b64encode(os.urandom(32)).decode(), encoding="utf-8")
    (backup / "manifest.json").write_text(
        json.dumps({"key_backup_name": queue_key.name}), encoding="utf-8"
    )
    encryption_key = os.urandom(32)
    encrypted = tmp_path / "bundle.aes256gcm"
    metadata = create_encrypted_bundle(backup, key_root, encrypted, encryption_key)
    assert metadata["timestamp"] == backup.name
    assert queue_key.read_bytes() not in encrypted.read_bytes()

    archive = tmp_path / "bundle.tar.gz"
    decrypt_file(encrypted, archive, encryption_key)
    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
    assert f"backup/{backup.name}/manifest.json" in names
    assert f"key-escrow/{queue_key.name}" in names
