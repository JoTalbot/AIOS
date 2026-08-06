#!/usr/bin/env python3
"""
AIOS Swarm Quant Backtester Runner
Запуск бэктестинга квант-стратегий и Swarm-дебатов Роя.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.swarm_quant_backtester import SwarmQuantBacktester

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunSwarmBacktester")

def main():
    backtester = SwarmQuantBacktester()
    res = backtester.run_backtest_simulation()
    print("\n=== AIOS SWARM QUANT BACKTEST & CONSENSUS RESULTS ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
