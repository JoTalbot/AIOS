#!/usr/bin/env python3
"""Cross-asset lead-lag study (Edge Lab external signals, 2026-08-17).

Untested hypothesis: BTC/ETH (leaders) move BEFORE alts at the hourly scale,
so leader returns at t-k predict alt returns at t (k=1..6h). If real and
large enough to survive 0.5% round-trip costs, it is a tradable signal
("trade alts on leader momentum") — an external data source the current
ML does not use.

Honest design:
- 1h closes, 1 year, binance proxy (data/quant/<SYM>/binance/*_1h.csv);
- per alt: Pearson corr of alt ret_t vs leader ret_{t-k}, k=0..6;
- tradable check on the LAST 30% of the window (no fitting): rule
  "long alt when BTC 6h momentum >= q80(history before window), exit after
  6h", net of 0.5% cost, vs always-long baseline;
- aggregated verdict: share of alts where leader-lag corr exceeds the
  contemporaneous corr materially AND the rule beats baseline.

Read-only; writes data/reports/lead_lag_report.md.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
QUANT_DIR = REPO_ROOT / "data" / "quant"

LEADERS = ["BTC", "ETH"]
LAGS = [0, 1, 2, 3, 4, 5, 6]
COST = 0.005


def load_1h(symbol: str) -> pd.Series | None:
    csv_paths = sorted(QUANT_DIR.glob(f"{symbol}/binance/{symbol}_1h.csv"))
    if not csv_paths:
        return None
    df = pd.read_csv(csv_paths[0]).sort_values("timestamp_ms")
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp_ms"], unit="ms"))
    return s[~s.index.duplicated(keep="last")]


def lead_lag_row(leader: pd.Series, alt: pd.Series) -> dict | None:
    """Correlations of alt ret_t vs leader ret_{t-k} on the shared timeline."""

    common = leader.index.intersection(alt.index)
    if len(common) < 2000:
        return None
    lr = leader.reindex(common).pct_change().dropna()
    ar = alt.reindex(common).pct_change().dropna()
    idx = lr.index.intersection(ar.index)
    lr, ar = lr.reindex(idx), ar.reindex(idx)
    out = {}
    for k in LAGS:
        lv = lr.shift(k).values
        mask = np.isfinite(lv) & np.isfinite(ar.values)
        if mask.sum() < 100:
            out[k] = float("nan")
            continue
        out[k] = float(np.corrcoef(ar.values[mask], lv[mask])[0, 1])
    return out


def momentum_rule(leader: pd.Series, alt: pd.Series, *,
                  window_h: int = 6, quantile: float = 0.80,
                  hold_h: int = 6, cost: float = COST) -> dict | None:
    """Tradable check on the last 30% of the shared timeline: long alt when
    leader's window_h momentum exceeds the quantile computed on the earlier
    70%, hold for hold_h, net of cost."""

    common = leader.index.intersection(alt.index)
    if len(common) < 2000:
        return None
    alt_c = alt.reindex(common).dropna()
    leader_c = leader.reindex(common).dropna()
    idx = alt_c.index.intersection(leader_c.index)
    alt_c, leader_c = alt_c.reindex(idx), leader_c.reindex(idx)
    mom = leader_c.pct_change(window_h).dropna()
    idx = mom.index
    alt_c = alt_c.reindex(idx)
    a = alt_c.values
    m = mom.values
    n = len(a)
    split = int(n * 0.70)
    thr = float(np.quantile(m[:split], quantile))
    rets = []
    base = []
    for i in range(split, n - hold_h, hold_h):
        r = a[i + hold_h] / a[i] - 1.0
        base.append(r - cost)
        if m[i] >= thr:
            rets.append(r - cost)
    rets = np.asarray(rets) if rets else np.array([])
    base = np.asarray(base)
    if len(rets) < 20:
        return None
    return {
        "n_trades": int(len(rets)),
        "mean_pct": round(float(rets.mean()) * 100, 3),
        "positive_pct": round(float((rets > 0).mean()) * 100, 1),
        "baseline_mean_pct": round(float(base.mean()) * 100, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "data" / "reports" / "lead_lag_report.md")
    args = ap.parse_args()

    leaders = {s: load_1h(s) for s in LEADERS}
    leaders = {k: v for k, v in leaders.items() if v is not None}
    symbols = sorted(
        p.parent.parent.name
        for p in QUANT_DIR.glob("*/binance/*_1h.csv")
        if p.parent.parent.name not in LEADERS
    )

    rows = []
    for sym in symbols:
        alt = load_1h(sym)
        if alt is None:
            continue
        row = {"symbol": sym}
        for leader_name, leader in leaders.items():
            corr = lead_lag_row(leader, alt)
            if corr is not None:
                row[f"{leader_name}_lag0"] = corr[0]
                row[f"{leader_name}_lag1"] = corr[1]
                row[f"{leader_name}_lag3"] = corr[3]
                row[f"{leader_name}_lag6"] = corr[6]
            rule = momentum_rule(leader, alt) if leader_name == "BTC" else None
            if rule is not None:
                row["rule"] = rule
        if "BTC_lag0" in row:
            rows.append(row)
        print(f"{sym}: {row.get('BTC_lag0')} {row.get('BTC_lag1')} {row.get('BTC_lag6')} "
              f"rule={row.get('rule')}", flush=True)

    # aggregates
    lag0 = np.array([r["BTC_lag0"] for r in rows])
    lag1 = np.array([r["BTC_lag1"] for r in rows])
    lag3 = np.array([r["BTC_lag3"] for r in rows])
    lag6 = np.array([r["BTC_lag6"] for r in rows])
    rules = [r["rule"] for r in rows if "rule" in r]
    beats = sum(1 for r in rules if r["mean_pct"] > r["baseline_mean_pct"])
    pos_rules = sum(1 for r in rules if r["mean_pct"] > 0)

    lines = [
        "# Lead-lag: лидеры (BTC/ETH) ведут альты на 1h? (Edge Lab 2026-08-17)",
        "",
        f"Альтов: {len(rows)} | корреляции alt_ret_t vs BTC_ret_{'{t-k}'} на годовой истории 1h:",
        "",
        f"- lag0 (одновременно): mean {lag0.mean():.3f} (медиана {np.median(lag0):.3f})",
        f"- lag1 (BTC на 1ч раньше): mean {lag1.mean():.3f} (медиана {np.median(lag1):.3f})",
        f"- lag3: mean {lag3.mean():.3f} | lag6: mean {lag6.mean():.3f}",
        "",
        "Чтение: если BTC реально «ведёт», corr(lag1..6) должен быть сопоставим с lag0;",
        "если corr падает к нулю уже на lag1 — рынок синхронный, lead-lag нет.",
        "",
        "## Торгуемая проверка (последние 30% окна, без подгонки)",
        "",
        "Правило: long альт при 6h-моментуме BTC ≥ q80(истории до окна), выход через 6h, издержки 0.5%.",
        "",
        f"Альтов с правилом: {len(rules)} | правило > baseline: {beats} | правило > 0: {pos_rules}",
        "",
        "| Символ | BTC lag0 | BTC lag1 | BTC lag3 | BTC lag6 | rule mean | baseline | n |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        rule = r.get("rule")
        if rule:
            lines.append(
                f"| {r['symbol']} | {r['BTC_lag0']:.3f} | {r['BTC_lag1']:.3f} | {r['BTC_lag3']:.3f} "
                f"| {r['BTC_lag6']:.3f} | {rule['mean_pct']:+.2f}% | {rule['baseline_mean_pct']:+.2f}% | {rule['n_trades']} |"
            )
        else:
            lines.append(
                f"| {r['symbol']} | {r['BTC_lag0']:.3f} | {r['BTC_lag1']:.3f} | {r['BTC_lag3']:.3f} "
                f"| {r['BTC_lag6']:.3f} | — | — | — |"
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
