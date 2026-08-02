#!/usr/bin/env python3
"""
AIOS Backup Sessions — резервное копирование критичных сессий:
  • data/tg_userbot.session*  (личный Telegram)
  • data/chrome_twin/default  (все залогиненные аккаунты в Chrome)
  • .env (ключи)
  • data/*.json (шаблоны, финансы, напоминания, подписки)

В backups/sessions/<date>.tar.gz. Ротация: 7 копий.
Запуск по systemd-таймеру (ежедневно).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "backups" / "sessions"
KEEP = 7


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d_%H%M")
    out = DEST / f"sessions_{date}.tar.gz"

    targets = [
        ROOT / "data" / "tg_userbot.session",
        ROOT / "data" / "tg_userbot.session-journal",
        ROOT / ".env",
    ]
    # json-файлы данных
    for f in (ROOT / "data").glob("*.json"):
        targets.append(f)
    # Chrome-профиль (большой — tar отдельно)
    profile = ROOT / "data" / "chrome_twin" / "default"

    existing = [t for t in targets if t.exists() and t.is_file()]
    print(f"Файлов для бэкапа: {len(existing)} (+ Chrome-профиль {profile.exists()})")

    cmd = ["tar", "-czf", str(out)]
    for t in existing:
        cmd.append("-C")
        cmd.append(str(t.parent))
        cmd.append(t.name)
    if profile.exists():
        cmd += ["-C", str(profile.parent), "default"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print("Ошибка tar:", r.stderr[-300:])
            return 1
    except Exception as e:
        print("Ошибка:", e)
        return 1

    size = out.stat().st_size if out.exists() else 0
    print(f"Бэкап создан: {out} ({size // 1024 // 1024} MB)")

    # ротация
    backups = sorted(DEST.glob("sessions_*.tar.gz"))
    for old in backups[:-KEEP]:
        old.unlink()
        print(f"Удалён старый: {old.name}")
    print(f"Осталось копий: {len(backups[-KEEP:])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
