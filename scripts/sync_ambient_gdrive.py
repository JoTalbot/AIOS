#!/usr/bin/env python3
"""
AIOS Ambient Voice Recordings Downloader (Google Drive 14rdX3nrhBsv049uI_hql5dYuQDniQVft)
"""

import os
import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AMBIENT_DIR = REPO_ROOT / "Calls" / "!voice" / "ambient_drive"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.ambient_sync")


def sync_ambient():
    import gdown
    AMBIENT_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://drive.google.com/drive/folders/14rdX3nrhBsv049uI_hql5dYuQDniQVft"
    logger.info(f"📂 Загрузка фоновых записей окружения/диктофона из Гугл Диска в {AMBIENT_DIR}...")
    try:
        gdown.download_folder(url=url, output=str(AMBIENT_DIR), quiet=False)
    except Exception as e:
        logger.warning(f"Note: {e}")

    files = [f for f in AMBIENT_DIR.rglob("*") if f.is_file() and f.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}]
    logger.info(f"🎉 Записей окружения на диске: {len(files)} шт.")


if __name__ == "__main__":
    sync_ambient()
