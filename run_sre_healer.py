#!/usr/bin/env python3
"""
AIOS SRE Self-Reflective Crash Healer Entrypoint
Фоновый сканер ошибок логов и авто-исправление багов в коде.
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.sre_healer import SRESelfReflectiveHealer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunSREHealer")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS SRE Self-Reflective Healer")
    parser.add_argument("--log", type=str, default="/root/AIOS/logs/telegram_bot.log", help="Лог-файл для сканирования")
    parser.add_argument("--heal", action="store_true", help="Автоматически исправить последний найденный баг")
    args = parser.parse_args()

    healer = SRESelfReflectiveHealer()
    
    logger.info(f"🔎 [RunSREHealer] Сканирование лога: {args.log}...")
    tb_info = healer.scan_log_for_traceback(args.log)
    
    if not tb_info:
        print(json.dumps({
            "status": "success",
            "message": "В логе не обнаружено свежих трейсбеков Python. Все системы здоровы!"
        }, ensure_ascii=False, indent=2))
        return
        
    logger.warning(f"🚨 [RunSREHealer] Обнаружен сбой в {tb_info['file_path']} на строке {tb_info['line_number']}!")
    
    if args.heal:
        res = healer.apply_ai_fix(tb_info)
        print("\n=== AI SRE SELF-HEALING TRANSACTION RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("\n=== AI SRE DETECTED ERROR PREVIEW ===")
        print(json.dumps(tb_info, indent=2, ensure_ascii=False))
        print("\nДля авто-исправления запустите с флагом --heal")


if __name__ == "__main__":
    main()
