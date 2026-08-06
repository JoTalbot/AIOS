#!/usr/bin/env python3
"""
AIOS Treasury Manager Entrypoint
Управление казначейством системы, расчет резервов, мониторинг процентных ставок и проведение депозитов/выводов в DeFi Aave V3.
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

from aios_core.treasury_manager import AIOSTreasuryManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunTreasury")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Treasury & DeFi Reinvestment Manager")
    parser.add_argument("--audit", action="store_true", help="Провести аудит казначейства и рассчитать свободные средства (по умолчанию)")
    parser.add_argument("--rates", action="store_true", help="Запросить и вывести текущие процентные ставки (lending APY) в Aave и Compound")
    parser.add_argument("--reinvest", type=float, help="Физически реинвестировать указанную сумму в USD (USDT Polygon) в Aave V3")
    parser.add_argument("--withdraw", type=float, help="Физически вывести указанную сумму в USD (USDT Polygon) из Aave V3 обратно на горячий кошелек")
    args = parser.parse_args()

    manager = AIOSTreasuryManager()

    if args.reinvest:
        logger.info(f"💰 [RunTreasury] Запуск реальной On-Chain транзакции реинвестирования: ${args.reinvest:.2f} в Aave V3...")
        audit_res = manager.audit_reserves()
        if audit_res.get("system_budget_usd", 0.0) < args.reinvest:
            print(json.dumps({
                "status": "error",
                "error": f"Недостаточно средств в бюджете системы: доступно ${audit_res.get('system_budget_usd')}, затребовано ${args.reinvest}"
            }, ensure_ascii=False, indent=2))
            return

        res = manager.execute_aave_reinvestment(args.reinvest)
        print("\n=== REINVESTMENT TRANSACTION RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    elif args.withdraw:
        logger.info(f"🔓 [RunTreasury] Запуск реальной On-Chain транзакции вывода: ${args.withdraw:.2f} из Aave V3...")
        audit_res = manager.audit_reserves()
        if audit_res.get("active_aave_deposit_usd", 0.0) < args.withdraw:
            print(json.dumps({
                "status": "error",
                "error": f"Недостаточно средств на депозите Aave V3: доступно ${audit_res.get('active_aave_deposit_usd')}, затребовано ${args.withdraw}"
            }, ensure_ascii=False, indent=2))
            return
            
        res = manager.execute_aave_withdrawal(args.withdraw)
        print("\n=== WITHDRAWAL TRANSACTION RESULT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    elif args.rates:
        logger.info("📡 [RunTreasury] Запрос текущих ставок доходности в DeFi...")
        res = manager.check_defi_yields()
        print("\n=== DEFI LENDING APY RATES ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    else:
        # Проводим аудит свободных средств
        res = manager.audit_reserves()
        print("\n=== AIOS TREASURY AUDIT RESULTS ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
