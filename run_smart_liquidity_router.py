#!/usr/bin/env python3
"""
AIOS Smart Liquidity Router Runner v19.1
Запуск анализа доходностей между 4 сетями (Polygon/Base/Arbitrum/Solana) и ребалансировки.

Usage:
  python run_smart_liquidity_router.py                  # scan only (json)
  python run_smart_liquidity_router.py --telegram       # telegram report
  python run_smart_liquidity_router.py --dry-run        # dry-run rebalance quote
  python run_smart_liquidity_router.py --execute        # live (requires confirm + key)
  python run_smart_liquidity_router.py --daemon --interval 3600  # daemon mode
"""
import sys
import json
import time
import argparse
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.smart_liquidity_router import AIOSSmartLiquidityRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunLiquidityRouter")

def main():
    parser = argparse.ArgumentParser(description="AIOS Smart Liquidity Router v19.1")
    parser.add_argument("--telegram", action="store_true", help="Telegram markdown report")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run rebalance quote")
    parser.add_argument("--execute", action="store_true", help="Live execute rebalance (needs key + confirm)")
    parser.add_argument("--amount", type=float, default=None, help="Override amount USD for rebalance")
    parser.add_argument("--daemon", action="store_true", help="Daemon mode (loop)")
    parser.add_argument("--interval", type=int, default=3600, help="Daemon interval sec (default 3600)")
    parser.add_argument("--json", action="store_true", help="Force JSON output (default)")
    args = parser.parse_args()

    router = AIOSSmartLiquidityRouter()

    if args.daemon:
        logger.info(f"🚀 Liquidity Router daemon interval {args.interval}s")
        while True:
            try:
                res = router.scan_multi_chain_yields()
                router.save_state(res)
                logger.info(f"📊 Best {res['best_yield_strategy']['network']} {res['best_yield_strategy']['apy_pct']}% | Excess ${res['available_excess_capital_usd']} | Rebalance {res['rebalance_action_required']}")
                if res["rebalance_action_required"]:
                    dry = router.execute_rebalance(dry_run=True)
                    logger.info(f"🌉 Rebalance dry-run: {dry.get('from')}→{dry.get('to')} net +${dry.get('net_gain_annual_usd')}/yr fee ${dry.get('bridge_quote',{}).get('total_fee_usd')}")
                time.sleep(args.interval)
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                time.sleep(args.interval)
        return

    if args.telegram:
        report = router.generate_telegram_report()
        print(report)
        return

    if args.dry_run:
        res = router.execute_rebalance(dry_run=True, amount_usd=args.amount)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.execute:
        # safety confirm via env
        import os
        if os.getenv("AIOS_LIQUIDITY_LIVE", "0") != "1":
            print(json.dumps({"status": "blocked", "error": "Set AIOS_LIQUIDITY_LIVE=1 to allow live bridge. Dry-run only by default."}, indent=2, ensure_ascii=False))
            return
        res = router.execute_rebalance(dry_run=False, amount_usd=args.amount)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    # default scan
    res = router.scan_multi_chain_yields()
    print(json.dumps(res, indent=2, ensure_ascii=False))
    # save state
    try:
        router.save_state(res)
    except Exception:
        pass

if __name__ == "__main__":
    main()
