#!/usr/bin/env python3
"""
AIOS - Экспорт аналитических отчётов (бэктест, финансовый) на Google Диск.

Генерирует сводный отчёт по бэктесту всех активов и загружает на Google Диск
в папку AIOS_colab_models (через upload_gdrive.py).
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path

REPO = Path("/root/AIOS")
PY = "/opt/aios/.venv/bin/python"
OUT_DIR = REPO / "data" / "reports"
GDRIVE_FOLDER = "AIOS_colab_models"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_backtest_report():
    """Сводный бэктест по всем активам."""
    sys.path.insert(0, str(REPO))
    from aios_core.quant.backtest_ai_strategies import backtest_buy_hold, backtest_ml, _load_prices
    active = [d for d in os.listdir(REPO / "data" / "quant")
              if os.path.isdir(REPO / "data" / "quant" / d) and _load_prices(d)]
    rows = []
    for sym in sorted(active):
        bh = backtest_buy_hold(sym)
        ml = backtest_ml(sym, {})
        if "error" in bh or "error" in ml:
            continue
        rows.append({
            "symbol": sym,
            "buy_hold_pct": bh.get("total_return_pct"),
            "ml_pct": ml.get("total_return_pct"),
            "ml_sharpe": ml.get("sharpe"),
            "ml_maxdd": ml.get("max_drawdown_pct"),
            "ml_winrate": ml.get("win_rate_pct"),
        })
    rows.sort(key=lambda x: -(x["ml_pct"] or 0))
    return {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "assets": len(rows), "results": rows}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 1) бэктест
    log("Строю сводный бэктест-отчёт…")
    report = build_backtest_report()
    bt_file = OUT_DIR / "backtest_summary.json"
    bt_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Бэктест: {len(report['results'])} активов -> {bt_file}")

    # 2) загрузить на Google Диск
    log("Загружаю на Google Диск…")
    r = subprocess.run([PY, str(REPO / "scripts" / "upload_gdrive.py"),
                        "--dir", str(OUT_DIR), "--folder", GDRIVE_FOLDER],
                       capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        log("✅ Отчёт загружен на Google Диск")
    else:
        log(f"⚠️ Ошибка загрузки: {r.stderr[-200:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
