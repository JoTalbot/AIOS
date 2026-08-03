#!/usr/bin/env python3
"""Локальный защищённый бэкап профилей Signal и Viber.

Не копирует Chrome/WhatsApp-профиль: WhatsApp отложен пользователем, а профиль
Chrome существенно больше. Архивы остаются локально в ``backups/messenger_profiles``
с правами только для root.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUPS = ROOT / "backups" / "messenger_profiles"
RETENTION = int(os.environ.get("AIOS_MESSENGER_BACKUP_RETENTION", "14") or 14)
SOURCES = {
    "signal": Path("/root/.config/Signal"),
    "viber": Path("/root/.ViberPC"),
}
CACHE_PARTS = {"Cache", "Code Cache", "GPUCache", "DawnCache", "ShaderCache", "Crashpad"}


def _skip(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(info.name).parts
    if any(part in CACHE_PARTS for part in parts):
        return None
    # Не упаковываем потенциальные сокеты/FIFO; они не нужны для восстановления.
    if not (info.isfile() or info.isdir() or info.issym()):
        return None
    return info


def _secure(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


def backup(sources: dict[str, Path] | None = None, backups: Path | None = None,
           retention: int | None = None) -> dict:
    sources = sources or SOURCES
    backups = backups or BACKUPS
    retention = RETENTION if retention is None else retention
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    dest = backups / stamp
    suffix = 1
    while dest.exists():
        dest = backups / f"{stamp}_{suffix:02d}"
        suffix += 1
    dest.mkdir(parents=True, exist_ok=False)
    _secure(backups, 0o700)
    _secure(dest, 0o700)
    archive = dest / "profiles.tar.gz"
    included: list[dict] = []

    with tarfile.open(archive, "w:gz", compresslevel=6) as tar:
        for name, path in sources.items():
            if not path.exists():
                continue
            tar.add(path, arcname=name, recursive=True, filter=_skip)
            try:
                included.append({"name": name, "source": str(path), "bytes": path.stat().st_size})
            except OSError:
                included.append({"name": name, "source": str(path), "bytes": None})
    _secure(archive, 0o600)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive": archive.name,
        "profiles": included,
        "retention": retention,
    }
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _secure(manifest_path, 0o600)

    older = sorted((p for p in backups.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)[retention:]
    for directory in older:
        shutil.rmtree(directory, ignore_errors=True)
    return {"status": "ok", "backup": str(dest), "profiles": [x["name"] for x in included],
            "removed": len(older), "archive_bytes": archive.stat().st_size if archive.exists() else 0}


def main() -> int:
    result = backup()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
