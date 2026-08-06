#!/usr/bin/env python3
"""
AIOS Smart Liquidity Router Runner
Запуск анализа доходностей между сетями и выдача рекомендаций по ребалансировке.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.smart_liquidity_router import AIOSSmartLiquidityRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunLiquidityRouter")

def main():
    router = AIOSSmartLiquidityRouter()
    res = router.scan_multi_chain_yields()
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
