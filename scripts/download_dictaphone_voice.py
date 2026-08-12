#!/usr/bin/env python3
"""
AIOS Dictaphone & Ambient Voice Downloader
"""

import os
import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = REPO_ROOT / "Calls" / "!voice"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.download_voice")


def download_voice():
    import gdown
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://drive.google.com/drive/folders/1WHaRPR-_RVaCYh5J4n-DaezxZhY2Cmkd"
    logger.info("📂 Загрузка диктофонных записей из Google Drive !voice...")
    try:
        gdown.download_folder(url=url, output=str(VOICE_DIR), quiet=False)
    except Exception as e:
        logger.warning(f"Note: {e}")

    files = [f for f in VOICE_DIR.rglob("*") if f.is_file() and f.suffix.lower() in {".wav", ".m4a", ".mp3", ".ogg"}]
    logger.info(f"✅ Диктофонных файлов загружено: {len(files)}")


if __name__ == "__main__":
    download_voice()
