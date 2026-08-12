#!/usr/bin/env python3
"""WAL-safe backup, retention and restore drill for encrypted Telegram queues."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

DATABASES = {
    "telegram_outbox.sqlite3": "telegram_outbox",
    "telegram_generation.sqlite3": "telegram_generation",
    "telegram_canary_outbox.sqlite3": "telegram_outbox",
    "telegram_alert_outbox.sqlite3": "telegram_outbox",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_copy(source: Path, destination: Path, mode: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=destination.name + ".", dir=str(destination.parent))
    tmp = Path(name)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, destination)
    finally:
        tmp.unlink(missing_ok=True)


def _online_backup(source: Path, destination: Path) -> None:
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=20) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst, pages=256, sleep=0.01)
            dst.commit()
            # A source in WAL mode can transfer that persistent pragma. Force a
            # self-contained backup so restore never depends on sidecar files.
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dst.execute("PRAGMA journal_mode=DELETE").fetchone()
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError(f"integrity check failed for {source.name}")
    for suffix in ("-wal", "-shm"):
        Path(str(destination) + suffix).unlink(missing_ok=True)
    os.chmod(destination, 0o600)


def create_backup(
    *,
    data_dir: Path,
    backup_root: Path,
    key_file: Path,
    key_backup_root: Path,
    timestamp: str | None = None,
) -> Path:
    if not key_file.is_file() or not key_file.read_bytes().strip():
        raise RuntimeError("Telegram queue key is unavailable")
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root.mkdir(parents=True, exist_ok=True)
    key_backup_root.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_root, 0o700)
    os.chmod(key_backup_root, 0o700)
    final = backup_root / stamp
    if final.exists():
        raise FileExistsError(final)
    stage = backup_root / ("." + stamp + ".tmp")
    stage.mkdir(mode=0o700)
    key_copy = key_backup_root / f"{stamp}.key"
    try:
        _atomic_copy(key_file, key_copy, 0o600)
        files: dict[str, dict[str, object]] = {}
        for name, table in DATABASES.items():
            source = data_dir / name
            if not source.is_file():
                continue
            destination = stage / name
            _online_backup(source, destination)
            with sqlite3.connect(destination) as db:
                rows = int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                plaintext = int(
                    db.execute(f"SELECT COUNT(*) FROM {table} WHERE encrypted=0").fetchone()[0]
                )
            if plaintext:
                raise RuntimeError(f"plaintext rows found in {name}")
            files[name] = {
                "sha256": _sha256(destination),
                "size": destination.stat().st_size,
                "rows": rows,
                "table": table,
            }
        if not files:
            raise RuntimeError("no Telegram queue databases found")
        manifest = {
            "version": 1,
            "created_at": time.time(),
            "timestamp": stamp,
            "files": files,
            "key_backup_name": key_copy.name,
            "key_sha256": _sha256(key_copy),
        }
        manifest_path = stage / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.chmod(manifest_path, 0o600)
        os.replace(stage, final)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        key_copy.unlink(missing_ok=True)
        raise
    return final


def verify_backup(backup_dir: Path, key_backup_root: Path) -> dict:
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1:
        raise RuntimeError("unsupported backup manifest")
    key_file = key_backup_root / str(manifest["key_backup_name"])
    if not key_file.is_file() or _sha256(key_file) != manifest.get("key_sha256"):
        raise RuntimeError("backup key checksum mismatch")
    try:
        cipher = Fernet(key_file.read_bytes().strip())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("backup key is invalid") from exc
    checked = 0
    for name, metadata in manifest.get("files", {}).items():
        path = backup_dir / name
        if _sha256(path) != metadata.get("sha256"):
            raise RuntimeError(f"checksum mismatch for {name}")
        table = str(metadata["table"])
        with sqlite3.connect(path) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError(f"integrity check failed for {name}")
            active_statuses = (
                ("pending", "sending", "failed_unknown")
                if table == "telegram_outbox"
                else ("pending", "generating", "dead_letter")
            )
            placeholders = ",".join("?" for _ in active_statuses)
            rows = db.execute(
                f"SELECT text FROM {table} WHERE encrypted=1 "
                f"AND status IN ({placeholders})",
                active_statuses,
            ).fetchall()
            for row in rows:
                try:
                    cipher.decrypt(str(row[0]).encode("ascii"))
                except (InvalidToken, ValueError) as exc:
                    raise RuntimeError(f"active payload decrypt check failed for {name}") from exc
            checked += 1
    return {"databases": checked, "timestamp": manifest["timestamp"]}


def restore_to(backup_dir: Path, key_backup_root: Path, destination: Path) -> None:
    verify_backup(backup_dir, key_backup_root)
    destination.mkdir(parents=True, exist_ok=False)
    os.chmod(destination, 0o700)
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    _atomic_copy(backup_dir / "manifest.json", destination / "manifest.json", 0o600)
    for name in manifest["files"]:
        _atomic_copy(backup_dir / name, destination / name, 0o600)


def restore_drill(backup_dir: Path, key_backup_root: Path) -> dict:
    """Restore into an isolated temporary directory, then verify/decrypt it."""
    with tempfile.TemporaryDirectory(prefix="telegram-queue-restore-") as directory:
        restored = Path(directory) / "restored"
        restore_to(backup_dir, key_backup_root, restored)
        return verify_backup(restored, key_backup_root)


def rotate_backups(backup_root: Path, key_backup_root: Path, keep_days: int) -> int:
    cutoff = time.time() - max(1, keep_days) * 86400
    removed = 0
    for backup in backup_root.iterdir() if backup_root.exists() else []:
        if not backup.is_dir() or backup.name.startswith(".") or backup.stat().st_mtime >= cutoff:
            continue
        try:
            manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
            (key_backup_root / str(manifest.get("key_backup_name", ""))).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass
        shutil.rmtree(backup)
        removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("AIOS_TELEGRAM_STATE_DIR", "/root/AIOS/data")),
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AIOS_TELEGRAM_BACKUP_DIR", "/root/AIOS/backups/telegram-queues"
            )
        ),
    )
    parser.add_argument(
        "--key-file", type=Path, default=Path("/etc/aios/credentials/telegram_queue_key")
    )
    parser.add_argument(
        "--key-backup-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AIOS_TELEGRAM_KEY_BACKUP_DIR",
                "/root/aios-secret-backups/telegram-queue-keys",
            )
        ),
    )
    parser.add_argument("--keep-days", type=int, default=30)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--verify-latest", action="store_true")
    parser.add_argument("--restore-to", type=Path)
    args = parser.parse_args()

    verify_path = args.verify
    if args.verify_latest:
        candidates = sorted(
            path for path in args.backup_root.iterdir() if path.is_dir() and not path.name.startswith(".")
        ) if args.backup_root.exists() else []
        if not candidates:
            raise RuntimeError("no Telegram queue backup available for restore drill")
        verify_path = candidates[-1]

    if verify_path:
        result = restore_drill(verify_path, args.key_backup_root)
        if args.restore_to:
            restore_to(verify_path, args.key_backup_root, args.restore_to)
        print(f"telegram_queue_restore_drill=ok databases={result['databases']}")
        return 0

    backup = create_backup(
        data_dir=args.data_dir,
        backup_root=args.backup_root,
        key_file=args.key_file,
        key_backup_root=args.key_backup_root,
    )
    result = verify_backup(backup, args.key_backup_root)
    removed = rotate_backups(args.backup_root, args.key_backup_root, args.keep_days)
    print(
        f"telegram_queue_backup=ok databases={result['databases']} "
        f"rotation_removed={removed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
