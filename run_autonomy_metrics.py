#!/usr/bin/env python3
"""
AIOS Autonomy Metrics — экспорт метрик автономии в Prometheus-формате.

Пишет/обновляет файл (по умолчанию data/metrics_exporter/autonomy.prom),
который подхватывает aios-exporter. Метрики:
  aios_autonomy_decisions_total{decision=...}
  aios_autonomy_actions_total{action=...}
  aios_autonomy_sales_total
  aios_autonomy_approvals_pending
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "data" / "metrics_exporter" / "autonomy.prom"
# docker volume, который монтирует aios-exporter (source в контейнере)
VOLUME_OUT = Path("/var/lib/docker/volumes/aios_aios-data/_data/metrics_exporter/autonomy.prom")


def _collect() -> dict:
    from aios_core.autonomy.report import daily_summary
    s = daily_summary(days=30)
    # approvals pending
    pending = 0
    try:
        ap = json.loads((ROOT / "data" / "autonomy_approvals.json").read_text(encoding="utf-8"))
        pending = sum(1 for a in ap if a.get("status") == "pending")
    except Exception:
        pass
    return {
        "by_decision": s.get("by_decision", {}),
        "by_action": s.get("by_action", {}),
        "sales": s.get("sales", 0),
        "sales_amount": s.get("sales_amount", 0),
        "total": s.get("total_decisions", 0),
        "pending": pending,
    }


def _render(d: dict) -> str:
    lines = ["# HELP aios_autonomy_decisions_total Autonomy decisions",
             "# TYPE aios_autonomy_decisions_total counter"]
    for k, v in d["by_decision"].items():
        lines.append(f'aios_autonomy_decisions_total{{decision="{k}"}} {v}')
    lines += ["# HELP aios_autonomy_actions_total Autonomy actions",
              "# TYPE aios_autonomy_actions_total counter"]
    for k, v in d["by_action"].items():
        lines.append(f'aios_autonomy_actions_total{{action="{k}"}} {v}')
    lines += ["# HELP aios_autonomy_sales_total Autonomy-recorded sales",
              "# TYPE aios_autonomy_sales_total counter",
              f"aios_autonomy_sales_total {d['sales']}"]
    lines += ["# HELP aios_autonomy_sales_amount_total Sales amount",
              "# TYPE aios_autonomy_sales_amount_total gauge",
              f"aios_autonomy_sales_amount_total {d['sales_amount']}"]
    lines += ["# HELP aios_autonomy_approvals_pending Pending approvals",
              "# TYPE aios_autonomy_approvals_pending gauge",
              f"aios_autonomy_approvals_pending {d['pending']}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    out = DEFAULT_OUT
    if len(sys.argv) > 2 and sys.argv[1] == "--out":
        out = Path(sys.argv[2])
    d = _collect()
    text = _render(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    # также пишем в docker volume для aios-exporter
    try:
        VOLUME_OUT.parent.mkdir(parents=True, exist_ok=True)
        VOLUME_OUT.write_text(text, encoding="utf-8")
        print(f"метрики записаны в volume: {VOLUME_OUT}")
    except Exception as e:
        print(f"(volume недоступен: {e})")
    print(f"метрики записаны: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
