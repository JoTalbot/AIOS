#!/usr/bin/env python3
"""
AIOS - Автоматическое переобучение ML/RL моделей через Kaggle (systemd timer).

Запускает переобучение RL-агента на 33 активах через Kaggle API,
ждёт завершения, скачивает модель и загружает на Google Диск.

Запуск по расписанию (еженедельно):
    systemctl enable aios-kaggle-retrain.timer
"""
from __future__ import annotations

import os
import sys
import time
import json
import subprocess
from pathlib import Path

REPO = Path("/root/AIOS")
KAGGLE_CFG = "/root/.kaggle"
VENV_PY = "/opt/aios/.venv/bin/python"
KERNEL = "jotalbot/aios-rl-multi33"  # последний мультиактив
OUT = "/tmp/kaggle_retrain"

LOG = REPO / "logs" / "kaggle_retrain.log"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run(*args, timeout=600):
    env = dict(os.environ, KAGGLE_CONFIG_DIR=KAGGLE_CFG)
    r = subprocess.run([VENV_PY, "-m", "kaggle", *args],
                       capture_output=True, text=True, timeout=timeout, env=env, cwd=str(REPO))
    return r


def main():
    log("=== Старт автоматического переобучения ===")
    os.makedirs(OUT, exist_ok=True)

    # 1) запустить push последнего ноутбука (создаст новую версию и переобучит)
    nb_dir = REPO / "data" / "kg_multi33"
    if not nb_dir.exists():
        log("❌ папка ноутбука не найдена: " + str(nb_dir))
        return 1
    r = run("kernels", "push", "-p", str(nb_dir), timeout=120)
    log(f"Push: {r.stdout.strip()[-200:]} {r.stderr.strip()[-100:]}" if r.returncode != 0 else f"Push OK")

    # 2) ждать статуса COMPLETE
    for i in range(60):
        time.sleep(60)
        r = run("kernels", "status", KERNEL, timeout=60)
        status = r.stdout.strip()
        log(f"  [{i+1}] status: {status}")
        if "COMPLETE" in status:
            break
        if "ERROR" in status:
            log(f"❌ kernel ERROR: {r.stderr.strip()[-300:]}")
            return 2
    else:
        log("⏰ timeout ожидания (60 мин)")
        return 3

    # 3) скачать результат
    r = run("kernels", "output", KERNEL, "-p", OUT, timeout=120)
    log(f"Output: {r.stdout.strip()[-200:]}")

    # 4) скопировать модель в AIOS
    for f in Path(OUT).rglob("*.pt"):
        dest = REPO / "data" / "quant" / "models" / f.name
        import shutil
        shutil.copy(f, dest)
        log(f"✅ Модель обновлена: {f.name}")

    # 5) загрузить на Google Диск
    up = subprocess.run([VENV_PY, str(REPO / "scripts" / "upload_gdrive.py"),
                         "--dir", str(REPO / "data" / "quant" / "models"),
                         "--folder", "AIOS_colab_models"],
                        capture_output=True, text=True, timeout=300)
    log(f"Google Диск: {up.stdout.strip()[-200:] if up.returncode==0 else 'ERR '+up.stderr[-200:]}")

    log("=== Переобучение завершено ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
