#!/usr/bin/env python3
"""
AIOS Live On-Chain Revenue Listener Service Entrypoint
Запускает непрерывный сканер реальных блокчейн-поступлений в сетях Tron (TRC20) и EVM.
"""

import sys
import os
import time
import argparse
import logging
import json

sys.path.insert(0, "/root/AIOS")

from aios_core.live_onchain_listener import LiveOnChainRevenueListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunLiveOnChainListener")


def run_daemon(interval_seconds: int = 30):
    logger.info(f"🌐 [RunLiveOnChainListener] Запуск фонового сканера реальных блокчейн-поступлений (интервал: {interval_seconds} сек)...")
    listener = LiveOnChainRevenueListener()
    while True:
        try:
            res = listener.run_live_scan_loop()
            if res.get("real_incoming_detected", 0) > 0:
                logger.info(f"🚨 Обнаружен реальный входящий платеж на блокчейне! {json.dumps(res, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"❌ Ошибка блокчейн-сканера: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Live On-Chain Revenue Listener")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме фонового демона")
    parser.add_argument("--interval", type=int, default=30, help="Интервал демона в секундах (по умолчанию 30с)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
    else:
        listener = LiveOnChainRevenueListener()
        res = listener.run_live_scan_loop()
        print("\n=== AIOS LIVE ON-CHAIN SCAN RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
