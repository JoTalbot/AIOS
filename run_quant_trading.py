#!/usr/bin/env python3
"""AIOS paper-only quantitative trading service runner."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.quant_trading_engine import MultiExchangeQuantEngine, QuantMasterOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunQuantTrading")


def _env_enabled(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_engines():
    """Build isolated paper engines; legacy duplicate execution is opt-in."""

    legacy = QuantMasterOrchestrator() if _env_enabled("AIOS_QUANT_LEGACY_EXECUTION") else None
    filename = os.environ.get("AIOS_QUANT_PORTFOLIO_FILE", "multi_exchange_portfolios_v2.json")
    return legacy, MultiExchangeQuantEngine(portfolio_filename=filename)


def run_cycle(legacy, multi_engine) -> dict:
    """Run one cycle and return signals/trades/risk without real orders."""

    legacy_result = legacy.run_quant_cycle() if legacy is not None else {"signals": [], "legacy_execution": False}
    multi_result = multi_engine.run_multi_exchange_cycle()
    risk = multi_result.get("risk", {})
    logger.info(
        "🏛️ [DirectionalV2] trades=%s entry_mode=%s drawdown=%.3f%% daily=%.3f%% blocks=%s",
        len(multi_result.get("cycle_trades", [])),
        risk.get("entry_mode", "unknown"),
        float(risk.get("drawdown_pct", 0.0) or 0.0),
        float(risk.get("daily_loss_pct", 0.0) or 0.0),
        risk.get("block_reasons", {}),
    )
    for signal in legacy_result.get("signals", []):
        if signal.get("signal") != "HOLD":
            logger.info(
                "🚨 [QUANT SIGNAL] %s: %s confidence=%.1f%%",
                signal.get("symbol"),
                signal.get("signal"),
                float(signal.get("confidence", 0.0)) * 100.0,
            )
    return {"legacy": legacy_result, "multi": multi_result}


def run_daemon(interval_seconds: int = 900) -> None:
    logger.info("📈 Directional v2 paper daemon: interval=%ss (real orders disabled)", interval_seconds)
    legacy, multi_engine = build_engines()
    while True:
        try:
            run_cycle(legacy, multi_engine)
        except Exception:
            logger.exception("❌ Ошибка в цикле Directional v2")
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS cost-aware paper trading runner")
    parser.add_argument("--daemon", action="store_true", help="run continuously")
    parser.add_argument("--interval", type=int, default=900, help="daemon interval in seconds")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(interval_seconds=args.interval)
        return 0
    legacy, multi_engine = build_engines()
    print(json.dumps(run_cycle(legacy, multi_engine), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
