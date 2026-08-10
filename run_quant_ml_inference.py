#!/usr/bin/env python3
"""
AIOS Quant ML Engine - Демон инференса (Этап 2.3)

Периодически делает ML-прогноз направления цены по активам и сохраняет сигналы
в data/quant/ml_signals.json. Сигналы консультирующие (для quant_trading_engine
или человека), автоторговля не выполняется.

    python run_quant_ml_inference.py --daemon --interval 600
"""

from __future__ import annotations

import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.quant.ml_predictor import QuantMLPredictor  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.QuantMLInference")

SIGNALS_FILE = REPO_ROOT / "data" / "quant" / "ml_signals.json"


def run_once() -> dict:
    predictor = QuantMLPredictor()
    payload = predictor.signal_json()
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    SIGNALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SIGNALS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    n = sum(1 for s in payload.get("signals", []) if s.get("ok"))
    if predictor.available:
        logger.info("ML-сигналов по %d активам -> %s", n, SIGNALS_FILE)
    else:
        logger.warning("ML-модель не обучена. Запустите Colab-ноутбук Quant ML Training. (сигналов: %d)", n)
    return payload


def run_daemon(interval: int) -> None:
    logger.info("🔮 [QuantMLInference] Демон запущен (интервал %ss)...", interval)
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error("Ошибка цикла инференса: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AIOS Quant ML Inference Daemon")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    args = ap.parse_args()

    if args.daemon:
        run_daemon(args.interval)
    else:
        print(json.dumps(run_once(), indent=2, ensure_ascii=False)[:2000])
