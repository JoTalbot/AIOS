#!/usr/bin/env python3
"""
AIOS Crypto-to-Fiat Card Dispatcher Entrypoint
Запрос курсов обмена и вывод стейблкоинов USDT Polygon на банковские карты UAH.
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

from aios_core.fiat_dispatcher import AIOSFiatDispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunFiat")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Crypto-to-Card Fiat Dispatcher")
    parser.add_argument("--rate", type=float, help="Запросить курс обмена и сумму к получению для указанного объема USDT")
    parser.add_argument("--withdraw", nargs=2, metavar=("AMOUNT_USDT", "CARD_NUMBER"), help="Запустить обмен и вывод на карту: --withdraw 50 4149123456789012")
    parser.add_argument("--confirm", action="store_true", help="Реально отправить On-Chain транзакцию и завершить обмен")
    args = parser.parse_args()

    dispatcher = AIOSFiatDispatcher()

    if args.rate:
        logger.info(f"🔎 [RunFiat] Запрос курса обмена для ${args.rate:.2f} USDT...")
        res = dispatcher.get_fiat_exchange_rate(args.rate)
        print("\n=== FIAT EXCHANGE RATE PREVIEW ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    elif args.withdraw:
        amount_usdt, card_number = args.withdraw
        confirm = args.confirm
        
        logger.info(f"🚀 [RunFiat] Инициирован обмен {amount_usdt} USDT на карту {card_number} (Confirm: {confirm})...")
        res = dispatcher.execute_fiat_withdrawal(float(amount_usdt), card_number, confirm=confirm)
        print("\n=== FIAT WITHDRAWAL EXECUTION RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    else:
        # По умолчанию - показываем курс для $100
        logger.info("🔎 [RunFiat] Запрос дефолтного курса обмена для $100 USDT...")
        res = dispatcher.get_fiat_exchange_rate(100.0)
        print("\n=== DEFAULT FIAT EXCHANGE RATE (100 USDT) ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
