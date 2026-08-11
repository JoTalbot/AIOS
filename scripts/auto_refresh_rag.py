#!/usr/bin/env python3
"""
AIOS - Автопересборка личной RAG-базы (новые чаты + профиль) в ChromaDB.
Ежедневно (systemd timer).
"""
from __future__ import annotations

import sys
import time
import subprocess
from pathlib import Path

REPO = Path("/root/AIOS")
PY = "/opt/aios/.venv/bin/python"
LOG = REPO / "logs" / "rag_refresh.log"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run(script, *args):
    r = subprocess.run([PY, str(REPO / script), *args],
                       capture_output=True, text=True, timeout=600, cwd=str(REPO))
    return r


def main():
    log("=== Обновление RAG-базы ===")
    # 1) собрать личный корпус
    r = run("scripts/build_personal_knowledge.py")
    log(f"Корпус: {r.stdout.strip()[-200:] if r.returncode==0 else 'ERR '+r.stderr[-200:]}")
    # 2) построить fastembed коллекцию
    r = run("scripts/build_fastembed_collection.py")
    log(f"Fastembed: {r.stdout.strip()[-200:] if r.returncode==0 else 'ERR '+r.stderr[-200:]}")
    log("=== RAG-база обновлена ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
