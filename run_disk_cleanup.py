#!/usr/bin/env python3
"""
AIOS Disk Cleanup — ротация логов и старых бэкапов, чистка временных файлов.
  - логи старше 14 дней: обрезаем до последних 500KB
  - backups/ (кроме sessions): старше 30 дней удаляем
  - /tmp/aios_* и /tmp/viber_*, /tmp/*.png старше 3 дней удаляем
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
BACKUP_DIR = ROOT / "backups"
KEEP_LOG_DAYS = 14
KEEP_BACKUP_DAYS = 30
KEEP_TMP_DAYS = 3


def clean() -> dict:
    now = datetime.now()
    freed = 0
    details = []

    # логи: обрезать большие старые
    for f in LOG_DIR.glob("*.log"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if (now - mtime).days >= KEEP_LOG_DAYS and f.stat().st_size > 200 * 1024:
                before = f.stat().st_size
                # оставить последние 500KB
                data = f.read_bytes()
                f.write_bytes(data[-500 * 1024:])
                freed += before - f.stat().st_size
                details.append(f"лог {f.name}: {before // 1024}KB -> {f.stat().st_size // 1024}KB")
        except Exception:
            pass

    # бэкапы (кроме sessions — там сессии)
    for d in BACKUP_DIR.iterdir():
        if d.name == "sessions" or not d.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if (now - mtime).days >= KEEP_BACKUP_DAYS:
                size = sum(x.stat().st_size for x in d.rglob("*") if x.is_file())
                subprocess.run(["rm", "-rf", str(d)], timeout=30)
                freed += size
                details.append(f"бэкап {d.name}: {size // 1024 // 1024}MB удалён")
        except Exception:
            pass

    # временные файлы
    for pat in ("/tmp/aios_*", "/tmp/viber_*", "/tmp/olx_*.png", "/tmp/ig_*.png", "/tmp/np_*.png"):
        for f in Path("/tmp").glob(pat.split("/")[-1]):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if (now - mtime).days >= KEEP_TMP_DAYS:
                    size = f.stat().st_size
                    f.unlink()
                    freed += size
                    details.append(f"tmp {f.name}: {size // 1024}KB")
            except Exception:
                pass

    # скриншоты телефона старше 7 дней
    shots = ROOT / "data" / "android_gateway" / "screenshots"
    if shots.exists():
        for f in shots.glob("*.png"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if (now - mtime).days >= 7:
                    size = f.stat().st_size
                    f.unlink()
                    freed += size
                    details.append(f"скриншот {f.name}: {size // 1024}KB")
            except Exception:
                pass

    return {"status": "ok", "freed_kb": freed // 1024, "details": details}


if __name__ == "__main__":
    import json
    r = clean()
    print(json.dumps(r, ensure_ascii=False))
    for d in r["details"]:
        print(" ", d)
