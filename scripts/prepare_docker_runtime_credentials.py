#!/usr/bin/env python3
"""Prepare group-readable Docker secrets in tmpfs for non-root containers."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from scripts.render_alertmanager_config import render

ROOT = Path(__file__).resolve().parents[1]


def _owner_uid() -> int:
    return 0 if os.geteuid() == 0 else os.getuid()


def _atomic_copy(source: Path, destination: Path, *, gid: int) -> None:
    value = source.read_bytes().strip()
    if not value:
        raise RuntimeError(f"required credential {source.name} is empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=destination.name + ".", dir=str(destination.parent))
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chown(temporary, _owner_uid(), gid)
        os.chmod(temporary, 0o440)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(source: Path, runtime: Path, *, gid: int) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    os.chown(runtime, _owner_uid(), gid)
    os.chmod(runtime, 0o750)
    for name in ("telegram_token", "telegram_owner_chat_id"):
        _atomic_copy(source / name, runtime / name, gid=gid)
    config = runtime / "alertmanager.yml"
    render(
        ROOT / "deploy/monitoring/alertmanager/alertmanager.yml.tmpl",
        runtime / "telegram_owner_chat_id",
        config,
    )
    os.chown(config, _owner_uid(), gid)
    os.chmod(config, 0o440)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=Path("/etc/aios/credentials")
    )
    parser.add_argument(
        "--runtime", type=Path, default=Path("/run/aios-docker-credentials")
    )
    parser.add_argument("--gid", type=int, default=65534)
    args = parser.parse_args()
    prepare(args.source, args.runtime, gid=args.gid)
    # Remove old persistent rendered chat metadata only after tmpfs is ready.
    if args.runtime == Path("/run/aios-docker-credentials"):
        Path("/etc/aios/alertmanager.yml").unlink(missing_ok=True)
    print("docker_runtime_credentials=prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
