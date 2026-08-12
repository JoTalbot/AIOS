#!/usr/bin/env python3
"""Move Telegram runtime state, logs and backups out of the Git checkout.

The migration is idempotent, checksum-verifies every copied file and never
prints file contents. Run while Telegram writers are stopped. Source files are
removed only with ``--remove-source`` after durable destination copies exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

STATE_NAMES = {
    "telegram_outbox.sqlite3",
    "telegram_generation.sqlite3",
    "telegram_canary_outbox.sqlite3",
    "telegram_alert_outbox.sqlite3",
    "telegram_metrics.jsonl",
    "telegram_metrics_summary.json",
    "telegram_metrics_alert_state.json",
    "telegram_colab_canary.json",
    "colab_recovery_metrics.json",
    "templates.json",
    "reminders.json",
}
LOG_NAMES = {
    "tg.log",
    "telegram_colab_canary.log",
    "telegram_metrics_report.log",
}


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _copy_verified(source: Path, destination: Path, mode: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=destination.name + ".", dir=str(destination.parent))
    temporary = Path(name)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.chmod(temporary, mode)
        if _digest(source) != _digest(temporary):
            raise RuntimeError(f"checksum mismatch while migrating {source.name}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _files_for_state(source: Path) -> list[Path]:
    result: list[Path] = []
    for name in sorted(STATE_NAMES):
        path = source / name
        if path.is_file():
            result.append(path)
        if name.endswith(".sqlite3"):
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(path) + suffix)
                if sidecar.is_file():
                    result.append(sidecar)
    return result


def _migrate_files(
    files: list[Path], destination: Path, *, remove_source: bool
) -> list[dict[str, object]]:
    migrated: list[dict[str, object]] = []
    for source in files:
        target = destination / source.name
        _copy_verified(source, target, 0o600)
        migrated.append(
            {"name": source.name, "size": target.stat().st_size, "sha256": _digest(target)}
        )
        if remove_source:
            source.unlink()
    return migrated


def _merge_tree(source: Path, destination: Path, *, remove_source: bool) -> int:
    if not source.exists():
        return 0
    copied = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            os.chmod(target, 0o700)
        elif path.is_file():
            _copy_verified(path, target, 0o600)
            copied += 1
    if remove_source:
        shutil.rmtree(source)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-state", type=Path, default=Path("/root/AIOS/data"))
    parser.add_argument("--source-logs", type=Path, default=Path("/root/AIOS/logs"))
    parser.add_argument(
        "--source-backups", type=Path, default=Path("/root/AIOS/backups/telegram-queues")
    )
    parser.add_argument(
        "--source-key-backups",
        type=Path,
        default=Path("/root/aios-secret-backups/telegram-queue-keys"),
    )
    parser.add_argument("--state", type=Path, default=Path("/var/lib/aios/telegram"))
    parser.add_argument("--logs", type=Path, default=Path("/var/log/aios/telegram"))
    parser.add_argument(
        "--backups", type=Path, default=Path("/var/backups/aios/telegram-queues")
    )
    parser.add_argument(
        "--key-backups",
        type=Path,
        default=Path("/var/backups/aios/telegram-queue-keys"),
    )
    parser.add_argument("--remove-source", action="store_true")
    args = parser.parse_args()

    for directory in (args.state, args.logs, args.backups, args.key_backups):
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)

    state = _migrate_files(
        _files_for_state(args.source_state), args.state, remove_source=args.remove_source
    )
    logs = _migrate_files(
        [args.source_logs / name for name in sorted(LOG_NAMES) if (args.source_logs / name).is_file()],
        args.logs,
        remove_source=args.remove_source,
    )
    backup_files = _merge_tree(
        args.source_backups, args.backups, remove_source=args.remove_source
    )
    key_files = _merge_tree(
        args.source_key_backups, args.key_backups, remove_source=args.remove_source
    )
    manifest = {
        "version": 1,
        "created_at": time.time(),
        "source_removed": bool(args.remove_source),
        "state": state,
        "logs": logs,
        "backup_files": backup_files,
        "key_backup_files": key_files,
    }
    target = args.state / "runtime_migration_manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)
    print(
        "telegram_runtime_migration=ok "
        f"state_files={len(state)} log_files={len(logs)} "
        f"backup_files={backup_files} key_files={key_files} "
        f"source_removed={int(args.remove_source)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
