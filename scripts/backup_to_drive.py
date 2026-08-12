#!/usr/bin/env python3
"""
AIOS - Резервное копирование важных данных на Google Диск.
Копирует: БД (aios, olx, профили), конфиги, модели, портфели, RAG-корпус, счета.
В отдельную папку AIOS_backup на Google Диске.
"""
from __future__ import annotations

import os
import sys
import json
import shutil
import time
import subprocess
from pathlib import Path

REPO = Path("/root/AIOS")
PY = "/opt/aios/.venv/bin/python"
STAGE = REPO / "data" / "backup_stage"
GDRIVE_FOLDER = "AIOS_backup"

# что бэкапим: (исходник, имя в бэкапе)
BACKUP_ITEMS = [
    ("data/aios.sqlite", "aios.sqlite"),
    ("data/olx_http.sqlite", "olx_http.sqlite"),
    ("data/olx_subs.sqlite", "olx_subs.sqlite"),
    ("data/aios.db", "aios.db"),
    ("data/multi_exchange_portfolios.json", "multi_exchange_portfolios.json"),
    ("data/quant/ml_signals.json", "ml_signals.json"),
    ("data/quant/rl_signals.json", "rl_signals.json"),
    ("data/quant/models/ppo_v4.pt", "ppo_v4.pt"),
    ("data/quant/models/catboost_price_dir.cbm", "catboost_price_dir.cbm"),
    ("data/quant/models/catboost_price_dir.pkl", "catboost_price_dir.pkl"),
    ("data/quant/models/lstm_price_dir.pt", "lstm_price_dir.pt"),
    ("data/quant/clustering/clustering_result.json", "clustering_result.json"),
    ("data/quant/backtest_results.json", "backtest_results.json"),
    ("data/rag/corpus_personal.jsonl", "corpus_personal.jsonl"),
    ("data/reports/backtest_summary.json", "backtest_summary.json"),
    (".env", "aios.env"),
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    n = 0
    for src_rel, name in BACKUP_ITEMS:
        src = REPO / src_rel
        if not src.exists():
            continue
        dst = STAGE / name
        try:
            shutil.copy2(src, dst)
            n += 1
        except Exception as e:
            log(f"  ⚠️ {name}: {e}")
    log(f"Скопировано {n} файлов в staging")

    # загрузить на Google Диск через upload_gdrive (обходит rate-limit)
    r = subprocess.run([PY, str(REPO / "scripts" / "upload_gdrive.py"),
                        "--dir", str(STAGE), "--folder", GDRIVE_FOLDER],
                       capture_output=True, text=True, timeout=400)
    if r.returncode == 0:
        log(f"✅ Резервная копия загружена на Google Диск ({n} файлов)")
    else:
        log(f"⚠️ Ошибка загрузки: {r.stderr[-200:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
