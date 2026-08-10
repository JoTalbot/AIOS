#!/usr/bin/env python3
"""
AIOS Google Drive Calls Downloader
Скачивает аудиозаписи звонков из Гугл Диска (1zAKjmh0Yh92SkJ-erYy4Xafhv19VY-yN) в /root/AIOS/Calls/
"""

import os
import sys
import re
import json
import logging
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CALLS_DIR = REPO_ROOT / "Calls"

GDRIVE_FOLDER_ID = "1zAKjmh0Yh92SkJ-erYy4Xafhv19VY-yN"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.gdrive_calls")


def sync_gdrive():
    CALLS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"📂 Запуск gdown для папки Гугл Диска ID: {GDRIVE_FOLDER_ID}...")

    import gdown
    folder_url = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
    try:
        gdown.download_folder(url=folder_url, output=str(CALLS_DIR), quiet=False, remaining_ok=True)
    except Exception as e:
        logger.warning(f"Note on download_folder: {e}")

    # Сканирование результатов
    files = list(CALLS_DIR.rglob("*"))
    audio_files = [f for f in files if f.is_file() and f.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}]
    logger.info(f"🎉 Всего файлов в /root/AIOS/Calls: {len(files)}, из них аудиозаписей звонков: {len(audio_files)}")


if __name__ == "__main__":
    sync_gdrive()
