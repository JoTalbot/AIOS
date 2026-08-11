#!/usr/bin/env python3
"""Безопасная очистка диска: старые бэкапы, tmp, дубли, ротация логов."""
import os
import shutil
import subprocess
from pathlib import Path

AIOS = Path("/root/AIOS")
DRY = "--dry-run" in __import__("sys").argv


def human(n):
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}ГБ"


def rm(path, desc):
    if not os.path.exists(path):
        return 0
    try:
        sz = os.path.getsize(path) if os.path.isfile(path) else sum(
            os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs)
        if DRY:
            print(f"[DRY] удалить {desc}: {path} ({human(sz)})")
            return 0
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print(f"✅ удалено: {desc} ({human(sz)})")
        return sz
    except Exception as e:
        print(f"⚠️ ошибка {path}: {e}")
        return 0


total = 0

# 1) Старые ежедневные бэкапы (оставить последние 4 даты)
for sub in ["daily", "sessions", "messenger_profiles"]:
    d = AIOS / "backups" / sub
    if d.is_dir():
        # группируем по префиксу даты
        groups = {}
        for p in d.iterdir():
            key = p.name[:8] if sub == "daily" else p.name.replace("sessions_", "")[:8]
            if sub == "messenger_profiles":
                key = p.name[:8]
            groups.setdefault(key, []).append(p)
        sorted_keys = sorted(groups.keys())
        # оставить последние 4 даты
        to_del = sorted_keys[:-4] if len(sorted_keys) > 4 else []
        for key in to_del:
            for p in groups[key]:
                total += rm(str(p), f"старый бэкап {sub}/{p.name}")

# 2) tmp-файлы Kaggle
for d in ["/tmp/kgout1", "/tmp/kgout2", "/tmp/kgout3", "/tmp/kgout4",
          "/tmp/kgout5", "/tmp/kgout6", "/tmp/kgout7", "/tmp/kgout8", "/tmp/kgout9",
          "/tmp/kgclu", "/tmp/kgmulti", "/tmp/kgpull", "/tmp/kgout"]:
    total += rm(d, "tmp kaggle")

# 3) Старые Calls (обработанные, старше 60 дней)
calls = AIOS / "Calls"
if calls.is_dir():
    import time
    now = time.time()
    cutoff = 60 * 86400
    for f in calls.glob("*.json"):
        try:
            if now - f.stat().st_mtime > cutoff:
                total += rm(str(f), f"старый Call {f.name}")
        except Exception:
            pass

# 4) Дубли корпуса (оставить corpus.jsonl, удалить corpus_full)
total += rm(str(AIOS / "data" / "rag" / "corpus_full.jsonl"), "дубль корпуса corpus_full")

# 5) Ротация больших логов (оставить хвост 5000 строк)
for log in AIOS.glob("logs/*.log"):
    try:
        if log.stat().st_size > 5 * 1024 * 1024:  # >5MB
            if DRY:
                print(f"[DRY] ротация лога: {log.name}")
            else:
                with open(log, "r", errors="ignore") as f:
                    lines = f.readlines()
                with open(log, "w", errors="ignore") as f:
                    f.writelines(lines[-5000:])
                print(f"✅ ротация: {log.name} (оставлено {min(5000,len(lines))} строк)")
    except Exception as e:
        print(f"⚠️ лог {log.name}: {e}")

print(f"\nОсвобождено: {human(total)}" if total else "\nГотово (dry-run)")
