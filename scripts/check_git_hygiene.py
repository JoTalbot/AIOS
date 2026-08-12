#!/usr/bin/env python3
"""Fail CI when Git history contains oversized blobs or runtime secret files."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import PurePosixPath

BLOCKED_NAMES = {
    ".env",
    "telegram_token",
    "telegram_owner_chat_id",
    "telegram_queue_key",
    "telegram_offsite_backup_key",
    "telegram_queue.key",
}
BLOCKED_SUFFIXES = {".sqlite3-wal", ".sqlite3-shm"}


def history_blobs(revision: str = "--all") -> list[tuple[str, int, str]]:
    objects = subprocess.check_output(
        ["git", "rev-list", "--objects", revision], text=True
    ).splitlines()
    by_oid: dict[str, str] = {}
    for line in objects:
        oid, _, path = line.partition(" ")
        by_oid.setdefault(oid, path)
    request = "".join(oid + "\n" for oid in by_oid)
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input=request,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    blobs: list[tuple[str, int, str]] = []
    for line in result:
        oid, kind, size = line.split()
        if kind == "blob":
            blobs.append((oid, int(size), by_oid.get(oid, "")))
    return blobs


def violations(max_bytes: int, revision: str = "--all") -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for oid, size, path in history_blobs(revision):
        name = PurePosixPath(path).name
        blocked = name in BLOCKED_NAMES or any(path.endswith(s) for s in BLOCKED_SUFFIXES)
        if size > max_bytes or blocked:
            findings.append(
                {
                    "oid": oid,
                    "size": size,
                    "path": path,
                    "reason": "oversized" if size > max_bytes else "blocked-runtime-file",
                }
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024)
    parser.add_argument("--revision", default="--all")
    args = parser.parse_args()
    findings = violations(args.max_bytes, args.revision)
    print(f"git_hygiene_findings={len(findings)}")
    for finding in findings:
        # Paths, sizes and object IDs are safe; file contents are never read out.
        print(
            f"git_hygiene_violation={finding['reason']} size={finding['size']} "
            f"oid={str(finding['oid'])[:12]} path={finding['path']}"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
