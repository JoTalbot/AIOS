#!/usr/bin/env python3
"""
AIOS Master Autonomous Earnings Runner & Service Entrypoint
Запускает 100% цифровой, полностью автономный двигатель заработка AIOS.

ИСКЛЮЧЕНЫ: OLX, офлайн-товары, физическая перепродажа и участие человека.
ТОЛЬКО ЦИФРОВЫЕ АВТОНОМНЫЕ ВЕКТОРЫ (Автокод, Баунти, Обработка данных, AI Microservices).

РАСПРЕДЕЛЕНИЕ ПРИБЫЛИ (4 Кошелька по 25%):
1. Разработчик — 25%
2. Инвестор — 25%
3. Персонал — 25%
4. Система AIOS — 25% (расходуется по усмотрению системы)
"""

import sys
import os
import time
import argparse
import logging
import json

sys.path.insert(0, "/root/AIOS")

from aios_core.autonomous_earnings_engine import MasterAutonomousEarningsOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunAutonomousEarnings")


def run_single_cycle():
    logger.info("🚀 [RunAutonomousEarnings] Запуск разового цикла 100% цифрового автономного заработка...")
    orchestrator = MasterAutonomousEarningsOrchestrator()
    result = orchestrator.run_master_earnings_cycle()
    print("\n=== РЕЗУЛЬТАТ ЦИКЛА АВТОНОМНОГО ЦИФРОВОГО ЗАРАБОТКА ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def run_daemon(interval_seconds: int = 3600):
    logger.info(f"🔄 [RunAutonomousEarnings] Запуск фонового демона цифрового заработка (интервал: {interval_seconds} сек)...")
    orchestrator = MasterAutonomousEarningsOrchestrator()
    while True:
        try:
            res = orchestrator.run_master_earnings_cycle()
            summary = res.get("financial_summary", {})
            logger.info(
                f"📊 Сводка: Заработано за прогон: +${res.get('cycle_total_earned_usd'):.2f}, "
                f"Всего: ${summary.get('total_earned_all_time_usd'):.2f}, "
                f"Самообеспеченность Системы: {summary.get('system_sustainability_pct')}%"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле цифрового заработка: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Master Autonomous Digital Earnings Service")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме фонового демона")
    parser.add_argument("--interval", type=int, default=3600, help="Интервал демона в секундах (по умолчанию 3600с)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
    else:
        run_single_cycle()
