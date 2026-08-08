#!/usr/bin/env python3
"""
AIOS Freelance Brain Runner & Service Entrypoint
Запускает автономный мозг самообеспечения AIOS в режиме фонового демона или разового цикла.
Отправляет отклики и финансовые сводки владельцу в Telegram.
"""

import sys
import os
import time
import argparse
import logging
import json

# Добавляем корень проекта в путь
sys.path.insert(0, "/root/AIOS")

from aios_core.freelance_brain import FreelanceBrainManager
from aios_core.crypto_wallet import AIOSWalletManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunFreelanceBrain")


def run_single_cycle():
    logger.info("🧠 [RunFreelanceBrain] Запуск разового цикла фриланс-мозга...")
    brain = FreelanceBrainManager()
    result = brain.run_market_scan_cycle(max_process_batch=2)
    print("\n=== РЕЗУЛЬТАТ ЦИКЛА ФРИЛАНС-МОЗГА ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def run_daemon(interval_seconds: int = 3600):
    logger.info(f"🚀 [RunFreelanceBrain] Запуск фонового демона фриланс-мозга (интервал: {interval_seconds} сек)...")
    brain = FreelanceBrainManager()
    while True:
        try:
            res = brain.run_market_scan_cycle(max_process_batch=2)
            logger.info(f"📊 Сводка: Заработано ${res['income_earned_usd']:.2f}, Самообеспеченность: {res.get("financial_summary", {}).get("system_sustainability_pct", res.get("financial_summary", {}).get("self_sustainability_pct", 0.0))}%")
            # v21.22: повторные попытки для застрявших PROPOSAL_READY (не чаще cooldown)
            try:
                brain.retry_pending_submissions(max_retries=3, cooldown_sec=1800, batch=2)
            except Exception as e:
                logger.error(f"❌ Ошибка retry-цикла фриланс-мозга: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле фриланс-мозга: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Freelance Brain Service Runner")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме фонового демона")
    parser.add_argument("--interval", type=int, default=3600, help="Интервал демона в секундах (по умолчанию 3600с)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
    else:
        run_single_cycle()
