#!/usr/bin/env python3
"""Atomically install externally rotated runtime credentials without logging values."""

from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DIR = Path("/etc/aios/credentials")
DEFAULT_ROLLBACK = Path("/root/aios-secret-backups/credential-rotation")


def _atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value.rstrip(b"\n") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def rotate(
    *,
    credential_dir: Path,
    rollback_root: Path,
    telegram_token_file: Path | None = None,
    rotate_colab: bool = False,
) -> list[str]:
    changes: dict[str, bytes] = {}
    if telegram_token_file:
        token = telegram_token_file.read_bytes().strip()
        if not token or b":" not in token or len(token) < 20:
            raise RuntimeError("new Telegram token file is invalid")
        changes["telegram_token"] = token
    if rotate_colab:
        changes["colab_llm_api_key"] = secrets.token_urlsafe(36).encode("ascii")
    if not changes:
        raise RuntimeError("no credential rotation requested")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rollback = rollback_root / stamp
    rollback.mkdir(parents=True, mode=0o700)
    os.chmod(rollback_root, 0o700)
    os.chmod(rollback, 0o700)
    updated: list[str] = []
    try:
        for name, value in changes.items():
            target = credential_dir / name
            if target.exists():
                _atomic(rollback / name, target.read_bytes())
            _atomic(target, value)
            updated.append(name)
    except Exception:
        for name in updated:
            previous = rollback / name
            if previous.exists():
                _atomic(credential_dir / name, previous.read_bytes())
        raise
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--rollback-root", type=Path, default=DEFAULT_ROLLBACK)
    parser.add_argument("--telegram-token-file", type=Path)
    parser.add_argument("--rotate-colab-key", action="store_true")
    args = parser.parse_args()
    updated = rotate(
        credential_dir=args.credential_dir,
        rollback_root=args.rollback_root,
        telegram_token_file=args.telegram_token_file,
        rotate_colab=args.rotate_colab_key,
    )
    print("credentials_rotated=" + ",".join(sorted(updated)))
    print("controlled_restart_and_full_canary_required=yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
