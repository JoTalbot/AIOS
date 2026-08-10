#!/usr/bin/env python3
"""
AIOS Colab Farm - Фоновый демон Heartbeat-мониторинга (Этап 1)

Периодически health-check'ит все зарегистрированные Colab-сервисы и помечает
недоступные как degraded/offline. Запускать на VPS в фоне (как остальные run_*.py):

    python run_colab_heartbeat.py --daemon --interval 120
"""

from __future__ import annotations

import sys
import os
import time
import argparse
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent  # /root/AIOS
sys.path.insert(0, str(REPO_ROOT))

from aios_core.colab.colab_registry import colab_registry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AIOS.ColabHeartbeat")


def run_heartbeat(interval_seconds: int = 120, stale_seconds: float = 600.0) -> None:
    logger.info("💓 [ColabHeartbeat] Запуск мониторинга Colab-сервисов (интервал %ss)...", interval_seconds)
    while True:
        try:
            names = list(colab_registry.all().keys())
            if not names:
                logger.info("💓 Нет зарегистрированных Colab-сервисов. Ожидание...")
            else:
                for name in names:
                    res = colab_registry.health_check(name, timeout=6)
                    state = "🟢" if res["ok"] else "🔴"
                    logger.info("%s %s %s (%s)", state, res.get("kind", "?"), res["name"], res["url"])
                offline = colab_registry.mark_offline_stale(stale_seconds=stale_seconds)
                if offline:
                    logger.warning("⚠️ Помечены offline: %d сервисов", offline)
        except Exception as e:
            logger.error("Ошибка цикла heartbeat: %s", e)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AIOS Colab Farm Heartbeat Daemon")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=120)
    ap.add_argument("--stale", type=float, default=600.0)
    args = ap.parse_args()

    if args.daemon:
        run_heartbeat(interval_seconds=args.interval, stale_seconds=args.stale)
    else:
        names = list(colab_registry.all().keys())
        for name in names:
            print(colab_registry.health_check(name))
