#!/usr/bin/env python3
"""
AIOS DEX Arbitrage Scanner Runner
Запуск сканера спредов и арбитражных возможностей.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.dex_arbitrage_scanner import AIOSDEXArbitrageScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunArbitrageScanner")

def main():
    scanner = AIOSDEXArbitrageScanner()
    res = scanner.scan_arbitrage_opportunities()
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
