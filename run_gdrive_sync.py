#!/usr/bin/env python3
"""
AIOS Google Drive Sync Runner
CLI запуск синхронизации резервных копий и отчетов с Google Диском.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.gdrive_sync import AIOSGoogleDriveSync

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunGDriveSync")

def main():
    logger.info("☁️ [RunGDriveSync] Запуск синхронизации с Google Диском...")
    syncer = AIOSGoogleDriveSync()
    res = syncer.sync_all()
    print("\n=== AIOS GOOGLE DRIVE SYNC RESULT ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
