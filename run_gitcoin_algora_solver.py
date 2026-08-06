#!/usr/bin/env python3
"""
AIOS Gitcoin & Algora Bounty Solver Service Entrypoint
Запускает регулярный сканер и авто-исполнитель баунти-задач Gitcoin / Algora с отправкой Pull Request и комментариев на GitHub.
"""

import sys
import os
import time
import argparse
import logging
import json

sys.path.insert(0, "/root/AIOS")

from aios_core.gitcoin_algora_bounty_solver import GitcoinAlgoraMasterSolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunGitcoinAlgoraSolver")


def run_daemon(interval_seconds: int = 7200):
    logger.info(f"🎯 [RunGitcoinAlgoraSolver] Запуск фонового демона Gitcoin/Algora (интервал: {interval_seconds} сек)...")
    solver = GitcoinAlgoraMasterSolver()
    while True:
        try:
            res = solver.run_bounty_cycle(max_batch=1)
            summary = res.get("financial_summary", {})
            logger.info(
                f"📊 Сводка: Обработано баунти: {len(res.get('solved_results', []))}, "
                f"Начислено за прогон: +${res.get('total_earned_usd'):.2f}, "
                f"Самообеспеченность Системы: {summary.get('system_sustainability_pct')}%"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле Gitcoin/Algora: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Gitcoin Algora Bounty Solver Service")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме фонового демона")
    parser.add_argument("--interval", type=int, default=7200, help="Интервал демона в секундах (по умолчанию 7200с)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
    else:
        solver = GitcoinAlgoraMasterSolver()
        res = solver.run_bounty_cycle(max_batch=1)
        print("\n=== AIOS GITCOIN / ALGORA BOUNTY SOLVER RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
