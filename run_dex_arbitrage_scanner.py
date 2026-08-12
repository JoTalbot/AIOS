#!/usr/bin/env python3
"""
AIOS Flash-Loan Arbitrage Runner v19.2
Кросс-DEX/CEX скан + flash-loan симуляция.

Usage:
  python run_dex_arbitrage_scanner.py                      # legacy kraken internal
  python run_dex_arbitrage_scanner.py --cross              # cross-dex scan 4 venues
  python run_dex_arbitrage_scanner.py --cross --telegram   # telegram report
  python run_dex_arbitrage_scanner.py --simulate WETH binance kraken --amount 10000
  python run_dex_arbitrage_scanner.py --execute WETH binance kraken --amount 10000  # live needs AIOS_FLASH_LIVE=1
  python run_dex_arbitrage_scanner.py --daemon --interval 300
"""
import sys
import json
import time
import argparse
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.dex_arbitrage_scanner import AIOSFlashLoanArbitrageEngine, AIOSDEXArbitrageScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunArbitrageScanner")

# -- v20.0 Activation: TG-алерт при viable окне (антиспам 1/час) --------------
_LAST_ALERT_TS = [0.0]

def _load_env_var(name):
    if name in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if name in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    import os
    v = os.getenv(name)
    if v:
        return v
    env = Path("/root/AIOS/.env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def send_telegram_alert(text, cooldown_sec=3600):
    import urllib.request
    now = time.time()
    if now - _LAST_ALERT_TS[0] < cooldown_sec:
        return False
    token, chat = _load_env_var("TELEGRAM_BOT_TOKEN"), _load_env_var("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": text, "parse_mode": "HTML"}
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            _LAST_ALERT_TS[0] = now
            return True
    except Exception:
        return False
# ------------------------------------------------------------------------------



def main():
    parser = argparse.ArgumentParser(description="AIOS Flash-Loan Arbitrage v19.2")
    parser.add_argument("--cross", action="store_true", help="Cross-DEX/CEX scan (kraken/binance/cg/uni)")
    parser.add_argument("--telegram", action="store_true", help="Telegram report")
    parser.add_argument("--simulate", nargs=3, metavar=("SYMBOL","BUY_VENUE","SELL_VENUE"), help="Simulate flash loan: SYMBOL BUY SELL")
    parser.add_argument("--execute", nargs=3, metavar=("SYMBOL","BUY_VENUE","SELL_VENUE"), help="Live execute (needs AIOS_FLASH_LIVE=1)")
    parser.add_argument("--amount", type=float, default=10000, help="Flash loan amount USD (default 10000)")
    parser.add_argument("--min-spread", type=float, default=0.8, help="Min spread pct for cross scan (default 0.8)")
    parser.add_argument("--daemon", action="store_true", help="Daemon mode")
    parser.add_argument("--interval", type=int, default=300, help="Daemon interval sec (default 300)")
    args = parser.parse_args()

    engine = AIOSFlashLoanArbitrageEngine()

    if args.daemon:
        logger.info(f"🚀 Flash-Arb daemon interval {args.interval}s min_spread {args.min_spread}%")
        while True:
            try:
                res = engine.scan_cross_dex_opportunities(min_spread_pct=args.min_spread, flash_amount_usd=args.amount)
                engine.save_state(res)
                viable = res.get("viable_count", 0)
                best = res.get("best_opportunity")
                if best:
                    logger.info(f"📊 Best {best['pair']} {best['spread_pct']}% net10k ${best['flash_sim_10k']['net_profit_usd']} viable {best['viable']} | total viable {viable}")
                else:
                    logger.info(f"📊 No opportunities viable {viable}")
                if viable > 0:
                    opps = [o for o in res.get("opportunities", []) if o.get("viable")][:3]
                    if not opps and best:
                        opps = [best]
                    lines = [f"• {o['pair']}: spread {o['spread_pct']}% → net10k +${o['flash_sim_10k']['net_profit_usd']}" for o in opps]
                    if send_telegram_alert("🚨 <b>FLASH-ARB WINDOW</b>\n" + "\n".join(lines) + "\n#арбитраж"):
                        logger.info("🚨 TG-алерт отправлен")
                time.sleep(args.interval)
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                time.sleep(args.interval)
        return

    if args.simulate:
        sym, buy, sell = args.simulate
        res = engine.simulate_flash_loan(buy, sell, sym, amount_usd=args.amount)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.execute:
        sym, buy, sell = args.execute
        res = engine.execute_flash_arbitrage(sym, buy, sell, amount_usd=args.amount, dry_run=False)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.cross:
        res = engine.scan_cross_dex_opportunities(min_spread_pct=args.min_spread, flash_amount_usd=args.amount)
        if args.telegram:
            print(engine.generate_telegram_report())
        else:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        try:
            engine.save_state(res)
        except Exception:
            pass
        return

    if args.telegram:
        # legacy telegram for cross
        print(engine.generate_telegram_report())
        return

    # legacy default
    scanner = AIOSDEXArbitrageScanner()
    # This class now is alias to engine for backward compat, but keep old behavior via engine.scan_arbitrage...
    # Use engine's legacy wrapper
    res = engine.scan_arbitrage_opportunities()
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
