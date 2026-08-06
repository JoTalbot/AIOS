#!/usr/bin/env python3
"""
AIOS Quantitative Trading & Signal Radar Service Entrypoint
Запускает непрерывный количественный анализ рынков криптовалют, расчет индикаторов и симулятор бумажной торговли.
"""

import sys
import os
import time
import argparse
import logging
import json

sys.path.insert(0, "/root/AIOS")

from aios_core.quant_trading_engine import QuantMasterOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunQuantTrading")


def run_daemon(interval_seconds: int = 900):
    logger.info(f"📈 [RunQuantTrading] Запуск фонового количественного трейдинг-радара (интервал: {interval_seconds} сек)...")
    quant = QuantMasterOrchestrator()
    while True:
        try:
            res = quant.run_quant_cycle()
            for sig in res.get("signals", []):
                if sig.get("signal") != "HOLD":
                    logger.info(f"🚨 [QUANT SIGNAL!] {sig['symbol']}: {sig['signal']} (Confidence: {sig['confidence'] * 100}%) | {sig['reason']}")
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле Quant Engine: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Quant Trading & Signal Radar Service")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме фонового демона")
    parser.add_argument("--interval", type=int, default=900, help="Интервал демона в секундах (по умолчанию 900с = 15 мин)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
    else:
        quant = QuantMasterOrchestrator()
        res = quant.run_quant_cycle()
        print("\n=== AIOS QUANT TRADING ENGINE RESULTS ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
