#!/usr/bin/env python3
"""Encrypt and upload the latest Telegram queue backup to Backblaze B2.

Backblaze B2 is selected because its permanent free allowance covers the first
10 GB and its S3-compatible API supports Object Lock. The bucket must be
created with Object Lock enabled. No credential, bucket, endpoint, object key or
payload is printed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tarfile
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"AIOSB2\x00\x01"
NONCE_BYTES = 12
TAG_BYTES = 16


def _credential(name: str) -> bytes:
    directories = (
        os.environ.get("CREDENTIALS_DIRECTORY", ""),
        os.environ.get("AIOS_CREDENTIAL_SOURCE_DIR", "/etc/aios/credentials"),
    )
    for directory in directories:
        if not directory:
            continue
        try:
            value = (Path(directory) / name).read_bytes().strip()
        except OSError:
            continue
        if value:
            return value
    return b""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encryption_key() -> bytes:
    value = _credential("telegram_offsite_backup_key")
    try:
        decoded = base64.urlsafe_b64decode(value)
    except Exception:
        decoded = value
    if len(decoded) != 32:
        raise RuntimeError("offsite encryption key is unavailable or invalid")
    return decoded


def encrypt_file(source: Path, destination: Path, key: bytes) -> None:
    nonce = os.urandom(NONCE_BYTES)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(MAGIC)
        dst.write(nonce)
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            dst.write(encryptor.update(chunk))
        dst.write(encryptor.finalize())
        dst.write(encryptor.tag)
        dst.flush()
        os.fsync(dst.fileno())
    os.chmod(destination, 0o600)


def decrypt_file(source: Path, destination: Path, key: bytes) -> None:
    size = source.stat().st_size
    minimum = len(MAGIC) + NONCE_BYTES + TAG_BYTES
    if size < minimum:
        raise RuntimeError("encrypted backup is truncated")
    with source.open("rb") as src:
        if src.read(len(MAGIC)) != MAGIC:
            raise RuntimeError("encrypted backup header is invalid")
        nonce = src.read(NONCE_BYTES)
        src.seek(-TAG_BYTES, os.SEEK_END)
        tag = src.read(TAG_BYTES)
        ciphertext_end = size - TAG_BYTES
        src.seek(len(MAGIC) + NONCE_BYTES)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        with destination.open("wb") as dst:
            remaining = ciphertext_end - src.tell()
            while remaining:
                chunk = src.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError("encrypted backup is truncated")
                remaining -= len(chunk)
                dst.write(decryptor.update(chunk))
            dst.write(decryptor.finalize())
            dst.flush()
            os.fsync(dst.fileno())
    os.chmod(destination, 0o600)


def _latest_backup(backup_root: Path) -> Path:
    candidates = sorted(
        path
        for path in backup_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ) if backup_root.exists() else []
    if not candidates:
        raise RuntimeError("no local Telegram backup is available")
    return candidates[-1]


def create_encrypted_bundle(
    backup: Path, key_backup_root: Path, destination: Path, encryption_key: bytes
) -> dict[str, object]:
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    key_copy = key_backup_root / str(manifest["key_backup_name"])
    if not key_copy.is_file():
        raise RuntimeError("queue key escrow copy is unavailable")
    with tempfile.TemporaryDirectory(prefix="aios-offsite-tar-") as directory:
        archive = Path(directory) / "telegram-backup.tar.gz"
        with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
            tar.add(backup, arcname=f"backup/{backup.name}", recursive=True)
            tar.add(key_copy, arcname=f"key-escrow/{key_copy.name}", recursive=False)
        encrypt_file(archive, destination, encryption_key)
        # A local decrypt-and-hash round trip catches wrong key/format before upload.
        restored = Path(directory) / "roundtrip.tar.gz"
        decrypt_file(destination, restored, encryption_key)
        if _sha256(restored) != _sha256(archive):
            raise RuntimeError("offsite encryption round-trip mismatch")
    return {
        "timestamp": backup.name,
        "size": destination.stat().st_size,
        "sha256": _sha256(destination),
    }


def _config() -> dict[str, str]:
    return {
        "endpoint": os.environ.get("AIOS_B2_ENDPOINT", "").strip(),
        "region": os.environ.get("AIOS_B2_REGION", "").strip() or "us-west-004",
        "bucket": os.environ.get("AIOS_B2_BUCKET", "").strip(),
        "prefix": os.environ.get("AIOS_B2_PREFIX", "aios/telegram").strip("/"),
    }


def configured() -> bool:
    cfg = _config()
    return bool(
        cfg["endpoint"]
        and cfg["bucket"]
        and _credential("b2_access_key_id")
        and _credential("b2_secret_access_key")
        and _credential("telegram_offsite_backup_key")
    )


def upload_bundle(path: Path, metadata: dict[str, object], retention_days: int) -> None:
    import boto3
    from botocore.config import Config

    cfg = _config()
    client = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        region_name=cfg["region"],
        aws_access_key_id=_credential("b2_access_key_id").decode("utf-8"),
        aws_secret_access_key=_credential("b2_secret_access_key").decode("utf-8"),
        config=Config(signature_version="s3v4", retries={"max_attempts": 4, "mode": "standard"}),
    )
    object_key = f"{cfg['prefix']}/{metadata['timestamp']}.tar.gz.aes256gcm"
    retain_until = datetime.now(timezone.utc) + timedelta(days=max(1, retention_days))
    client.upload_file(
        str(path),
        cfg["bucket"],
        object_key,
        ExtraArgs={
            "ContentType": "application/octet-stream",
            "Metadata": {"sha256": str(metadata["sha256"]), "format": "aios-aes256gcm-v1"},
            "ObjectLockMode": "GOVERNANCE",
            "ObjectLockRetainUntilDate": retain_until,
        },
    )
    head = client.head_object(Bucket=cfg["bucket"], Key=object_key)
    if int(head.get("ContentLength", -1)) != int(metadata["size"]):
        raise RuntimeError("offsite object size verification failed")
    if str(head.get("Metadata", {}).get("sha256", "")) != str(metadata["sha256"]):
        raise RuntimeError("offsite object checksum metadata verification failed")


def _write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--prepare-only", type=Path)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=Path(os.environ.get("AIOS_TELEGRAM_BACKUP_DIR", "/var/backups/aios/telegram-queues")),
    )
    parser.add_argument(
        "--key-backup-root",
        type=Path,
        default=Path(os.environ.get("AIOS_TELEGRAM_KEY_BACKUP_DIR", "/var/backups/aios/telegram-queue-keys")),
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(os.environ.get("AIOS_TELEGRAM_STATE_DIR", "/var/lib/aios/telegram"))
        / "offsite_backup_state.json",
    )
    args = parser.parse_args()

    if args.check_config:
        print("offsite_backup_configured=" + ("yes" if configured() else "no"))
        return 0 if configured() else 1
    if not configured() and not args.prepare_only:
        _write_state(args.state_file, {"timestamp": time.time(), "configured": False, "ok": False})
        print("offsite_backup=skipped configured=no")
        return 0

    backup = _latest_backup(args.backup_root)
    key = _encryption_key()
    if args.prepare_only:
        metadata = create_encrypted_bundle(backup, args.key_backup_root, args.prepare_only, key)
        print(f"offsite_backup_prepare=ok size={metadata['size']}")
        return 0

    with tempfile.TemporaryDirectory(prefix="aios-offsite-") as directory:
        encrypted = Path(directory) / "backup.aes256gcm"
        metadata = create_encrypted_bundle(backup, args.key_backup_root, encrypted, key)
        upload_bundle(encrypted, metadata, args.retention_days)
    _write_state(
        args.state_file,
        {
            "timestamp": time.time(),
            "configured": True,
            "ok": True,
            "backup_timestamp": metadata["timestamp"],
            "size": metadata["size"],
            "sha256": metadata["sha256"],
            "retention_days": max(1, args.retention_days),
        },
    )
    print(f"offsite_backup=ok size={metadata['size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
