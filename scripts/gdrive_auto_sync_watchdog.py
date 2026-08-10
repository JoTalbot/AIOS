#!/usr/bin/env python3
"""
AIOS Google Drive Auto Sync Watchdog Service
Периодически проверяет Google Drive папки звонков и диктофона,
автоматически скачивает новые аудиофайлы, расшифровывает их, обновляет CRM Дашборд.
"""

import os
import sys
import time
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.download_gdrive_audio import download_all_audio
from scripts.download_ambient_direct_curl import download_ambient
from aios_core.whisper_colab_transcriber import process_calls_directory
from scripts.generate_standalone_calls_dashboard import build_preloaded_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aios.gdrive_watchdog")


def run_sync_cycle():
    logger.info("🔄 [GDrive Watchdog] Старт цикла синхронизации звонков и диктофонных записей...")
    
    # 1. Скачивание новых аудиозаписей звонков
    try:
        download_all_audio()
    except Exception as e:
        logger.warning(f"Note on call audio sync: {e}")

    # 2. Скачивание новых записей окружения (диктофона)
    try:
        download_ambient()
    except Exception as e:
        logger.warning(f"Note on ambient audio sync: {e}")

    # 3. Расшифровка и дикаризация
    try:
        results = process_calls_directory()
        logger.info(f"🎙️ Обработано новых файлов: {len(results)}")
    except Exception as e:
        logger.error(f"Ошибка расшифровки: {e}")

    # 4. Обновление Stitch CRM Дашборда
    try:
        build_preloaded_html()
        logger.info("🎉 Stitch CRM Дашборд успешно обновлен!")
    except Exception as e:
        logger.error(f"Ошибка обновления дашборда: {e}")


def main_loop(interval_seconds: int = 900):
    logger.info("🚀 [GDrive Watchdog Daemon] Сервис авто-синхронизации запущен!")
    while True:
        try:
            run_sync_cycle()
        except Exception as err:
            logger.error(f"Ошибка цикла синхронизации: {err}")
        
        logger.info(f"⏳ Ожидание {interval_seconds // 60} минут до следующей проверки Google Drive...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main_loop(900)
