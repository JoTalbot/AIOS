#!/usr/bin/env python3
"""
AIOS Direct Ambient Voice Downloader using direct usercontent URL
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AMBIENT_DIR = REPO_ROOT / "Calls" / "!voice" / "ambient_drive"

AMBIENT_FILES = [
    ("1Z3aLBEDBtgSFev2ZRARRuEwTXVAIdvbj", "2026_05_31_20_40_22.wav"),
    ("1ieIf5PpYEb9NX5FR2Az_0uw7jSoQopv_", "2026_05_31_21_00_43.wav"),
    ("109ujuOk1ABgsW5KUF3SBdf3_veUELSA-", "2026_05_31_21_21_00.wav"),
    ("1FavxLbSLqabuAtv_M_EcKhON4TFZjpT2", "2026_05_31_21_41_00.wav"),
    ("13E2WrYQa3mGSM4YiIuZtVs-Pf_OaI0pv", "2026_05_31_22_01_01.wav"),
    ("1CicdIhO-V6Hkt96v8DrvykT44sGb5e7k", "2026_05_31_22_21_01.wav"),
    ("1oNNxgoOFhLDJgF4lzActsLmiXUxoigMV", "2026_06_18_18_01_26.mp3"),
    ("1zq4mR1U3GGBrTq0RkUTPUk_BVTF07XGQ", "2026_08_07_20_09_49.mp3"),
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aios.ambient_direct")


def download_ambient():
    AMBIENT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for fid, fname in AMBIENT_FILES:
        out_path = AMBIENT_DIR / fname
        if out_path.exists() and out_path.stat().st_size > 1000:
            logger.info(f"✅ Файл уже загружен: {fname}")
            count += 1
            continue

        url = f"https://drive.usercontent.google.com/download?id={fid}&confirm=t"
        logger.info(f"📥 Загрузка фоновой записи: {fname}...")
        try:
            cmd = ["curl", "-L", "-s", url, "-o", str(out_path)]
            subprocess.run(cmd, check=True, timeout=120)
            if out_path.exists() and out_path.stat().st_size > 1000:
                logger.info(f"🎉 Успешно скачан: {fname} ({out_path.stat().st_size // (1024*1024)} MB)")
                count += 1
        except Exception as e:
            logger.warning(f"Ошибка скачивания {fname}: {e}")

    logger.info(f"🎉 Всего загружено диктофонных записей окружения: {count} шт.")


if __name__ == "__main__":
    download_ambient()
