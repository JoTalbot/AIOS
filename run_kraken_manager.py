#!/usr/bin/env python3
"""
AIOS Kraken Exchange Manager Entrypoint
Просмотр балансов, получение котировок и создание ордеров на бирже Kraken.
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

from aios_core.kraken_client import AIOSKrakenClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunKraken")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Kraken Exchange Manager")
    parser.add_argument("--balance", action="store_true", help="Запросить реальный баланс аккаунта Kraken (по умолчанию)")
    parser.add_argument("--ticker", type=str, help="Запросить живую котировку торговой пары (например, XBTUSD)")
    parser.add_argument("--trade", nargs=3, metavar=("PAIR", "SIDE", "VOLUME"), help="Исполнить реальный рыночный ордер: --trade ETHUSD buy 0.05")
    args = parser.parse_args()

    client = AIOSKrakenClient()

    if args.ticker:
        logger.info(f"🔎 [RunKraken] Запрос котировки для пары {args.ticker.upper()}...")
        res = client.get_ticker(args.ticker)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    elif args.trade:
        pair, side, volume = args.trade
        logger.info(f"🚀 [RunKraken] Создание РЕАЛЬНОГО ордера: {side.upper()} {volume} {pair.upper()}...")
        res = client.add_market_order(pair, side, float(volume))
        print("\n=== KRAKEN ORDER EXECUTION RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    else:
        # По умолчанию - опрашиваем баланс
        logger.info("🔎 [RunKraken] Запрос реального баланса аккаунта Kraken...")
        res = client.get_account_balance()
        print("\n=== KRAKEN ACCOUNT BALANCES ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
