#!/usr/bin/env python3
"""Production-accurate 3-month backtest of the CURRENT live strategy.

Reproduces the deployed Directional v2 paper engine 1:1 on historical data:
- config read from deploy/systemd/aios-quant-trading.service Environment
  (DirectionalV2Config.from_env after applying those env vars) -> current settings;
- per-exchange cash ($1000 each, INITIAL_PER_EXCHANGE), 30% cash reserve,
  min(investment, $200), min order $10, max 1 global position;
- entries on closed candle: static gates (exchange/positions/drawdown/daily/reserve),
  record_and_analyze signal + confidence, ML prob gate, RL veto (RL_ASSETS blocked);
- exits by hi/lo (SL/TP/trailing, harness convention) + confirmed_bearish_exit;
- kill switches: drawdown 0.25% and daily loss 0.25% of total equity (all 10 exchanges);
- prices: local 1h OHLCV CSVs for every allowed exchange that has data.

Also runs a sensitivity variant with trailing exit priced at bar close (live engine
prices trailing at current mid, not at the peak) and a control variant trail=0.988.

Usage:
    python scripts/quant_prod_3m_backtest.py [--months 3] [--output data/reports/prod_3m_backtest.md]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb

UNIT = REPO_ROOT / "deploy" / "systemd" / "aios-quant-trading.service"
RL_ASSETS = qmb.RL_ASSETS
COST = qmb.PROFILE["half_spread_rate"] + qmb.PROFILE["slippage_rate"]  # 0.001
FEE = qmb.PROFILE["fee_rate"]  # 0.0015


def load_unit_env() -> dict[str, str]:
    """Parse Environment= lines from the canonical systemd unit (current strategy)."""
    env: dict[str, str] = {}
    for line in UNIT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*Environment=([A-Z0-9_]+)=(.*)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def build_config(env: dict[str, str], trail_override: float | None = None):
    from aios_core.quant_directional_policy import DirectionalV2Config

    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update({k: v for k, v in env.items() if k.startswith("AIOS_QUANT")})
        if trail_override is not None:
            os.environ["AIOS_QUANT_TRAIL_RATIO"] = str(trail_override)
        cfg = DirectionalV2Config.from_env()
    finally:
        os.environ.clear()
        os.environ.update(old)
    return cfg


def load_series(env: dict[str, str], min_bars: int = 4000) -> tuple[dict[str, dict], dict[str, str]]:
    """Load 1h OHLCV for every (symbol, allowed-exchange) pair with local data.

    Picks the first allowed exchange with at least `min_bars` bars (kraken has only
    ~724 bars - API cap - and would silently truncate the test window otherwise).
    """
    allowed = [e.strip().lower() for e in env.get("AIOS_QUANT_ALLOWED_EXCHANGES", "").split(",")
               if e.strip()]
    out: dict[str, dict] = {}
    used: dict[str, str] = {}
    for sym_dir in sorted(Path(qmb.QUANT_DIR).iterdir()):
        sym = sym_dir.name
        if not sym_dir.is_dir() or sym in ("MATIC", "RNDR"):
            continue
        for ex in allowed:
            df = qmb._load_series(sym, ex)
            if df is None:
                continue
            if len(df) < min_bars:
                continue  # exchange history too short for the window
            feats = qmb._compute_features(df)
            out[f"{ex}:{sym}"] = {
                "symbol": sym,
                "exchange": ex,
                "df": df.reset_index(drop=True),
                "feats": feats.reset_index(drop=True),
                "closes": df["close"].values,
                "highs": df["high"].values,
                "lows": df["low"].values,
                "times": df["timestamp_ms"].values,
            }
            used.setdefault(sym, ex)
            break  # first allowed exchange with full history (unit order = priority)
    return out, used


def run_backtest(series: dict[str, dict], cfg, probs: dict[str, np.ndarray],
                 start_ms: int, *, trail_at_close: bool = False,
                 rl_block: bool = True) -> dict:
    """Event-driven simulation mirroring quant_directional_v2.run_multi_exchange_cycle."""
    from aios_core.quant_directional_policy import (
        bearish_exit_confirmed,
        entry_block_reason,
    )

    # per-exchange ledgers (all 10 engine exchanges, like the engine does)
    exchanges = ["kraken", "binance", "bybit", "okx", "uniswap_v3", "coinbase",
                 "kucoin", "bitfinex", "bitstamp", "mexc"]
    data = {ex: {"cash_usd": 1000.0, "initial_balance_usd": 1000.0,
                 "positions": {}, "entry_count": 0, "closed_trades": 0,
                 "winning_trades": 0, "net_profit_usd": 0.0, "net_loss_usd": 0.0,
                 "realized_pnl_usd": 0.0, "fees_paid_usd": 0.0} for ex in exchanges}

    # index series by timestamp
    by_ts: dict[int, list[tuple[str, dict]]] = defaultdict(list)
    for key, s in series.items():
        for k, ts in enumerate(s["times"]):
            if int(ts) >= start_ms:
                by_ts[int(ts)].append((key, s, k))
    all_ts = sorted(by_ts)

    # warm-up history (bars before start)
    history: dict[str, list[float]] = {}
    for key, s in series.items():
        i0 = int(np.searchsorted(s["times"], start_ms))
        history[key] = [float(c) for c in s["closes"][:i0]]

    block_counts: Counter[str] = Counter()
    trades: list[dict] = []
    equity_curve: list[dict] = []
    initial_total = 1000.0 * len(exchanges)
    peak_equity = initial_total
    day = ""
    day_start_equity = initial_total
    daily_loss_pct = 0.0

    def mark_equity() -> float:
        eq = sum(float(p["cash_usd"]) for p in data.values())
        for p in data.values():
            for pos in p["positions"].values():
                eq += float(pos["qty"]) * float(pos.get("mark_price", pos["entry_mid_price"]))
        return eq

    def global_positions() -> int:
        return sum(len(p["positions"]) for p in data.values())

    for ts in all_ts:
        now = ts / 1000.0
        d = datetime.fromtimestamp(ts / 1000, tz=UTC).strftime("%Y-%m-%d")
        if d != day:
            day = d
            day_start_equity = mark_equity()
            daily_loss_pct = 0.0

        # ---- exits ----
        for key, s, k in by_ts[ts]:
            ex = s["exchange"]
            price = float(s["closes"][k])
            history[key].append(price)
            pos = data[ex]["positions"].get(f"{s['symbol']}USD")
            if pos is None:
                continue
            pos["mark_price"] = price
            entry_mid = float(pos["entry_mid_price"])
            invested = float(pos["invested_usd"])
            qty = float(pos["qty"])
            max_seen = max(float(pos["max_price_seen"]), price)
            pos["max_price_seen"] = max_seen
            hi, lo = float(s["highs"][k]), float(s["lows"][k])
            exit_px = None
            reason = ""
            if lo <= entry_mid * (1.0 + cfg.stop_loss_pct):
                exit_px = entry_mid * (1.0 + cfg.stop_loss_pct) * (1.0 - COST)
                reason = "stop_loss"
            elif hi >= entry_mid * (1.0 + cfg.take_profit_pct):
                exit_px = entry_mid * (1.0 + cfg.take_profit_pct) * (1.0 - COST)
                reason = "take_profit"
            elif max_seen > entry_mid * 1.01 and lo <= max_seen * cfg.trail_ratio:
                exit_px = (max_seen * cfg.trail_ratio if not trail_at_close else price) * (1.0 - COST)
                reason = "trailing_stop"
            else:
                ml_prob = float(s["probs"][k]) if k < len(s["probs"]) and not np.isnan(s["probs"][k]) else None
                an = qmb.record_and_analyze(
                    history[key], ml_prob,
                    (0.0 if s["symbol"] in RL_ASSETS else None) if rl_block else None)
                if (an["signal"] == "SELL_SHORT"
                        and float(an["confidence"]) >= cfg.min_confidence
                        and ml_prob is not None and ml_prob <= cfg.bearish_ml_max
                        and (ts - pos["opened_at"]) >= cfg.min_hold_seconds * 1000):
                    exit_px = price * (1.0 - COST)
                    reason = "confirmed_bearish_exit"
            if exit_px is not None:
                proceeds = exit_px * qty
                net = proceeds - invested - exit_px * qty * FEE
                data[ex]["cash_usd"] += proceeds - exit_px * qty * FEE
                data[ex]["realized_pnl_usd"] += net
                data[ex]["fees_paid_usd"] += exit_px * qty * FEE
                data[ex]["closed_trades"] += 1
                if net > 0:
                    data[ex]["winning_trades"] += 1
                    data[ex]["net_profit_usd"] += net
                else:
                    data[ex]["net_loss_usd"] += abs(net)
                del data[ex]["positions"][f"{s['symbol']}USD"]
                trades.append({"symbol": s["symbol"], "exchange": ex, "net": net,
                               "pct": net / invested * 100.0, "reason": reason,
                               "opened_at": pos["opened_at"], "closed_at": ts,
                               "hold_h": round((ts - pos["opened_at"]) / 3_600_000, 1)})

        # ---- entries ----
        equity = mark_equity()
        peak_equity = max(peak_equity, equity)
        drawdown_pct = max(0.0, (initial_total - equity) / initial_total * 100.0)
        daily_loss_pct = max(daily_loss_pct,
                             max(0.0, (day_start_equity - equity) / day_start_equity * 100.0))
        for key, s, k in by_ts[ts]:
            ex = s["exchange"]
            sym = s["symbol"]
            pos = data[ex]["positions"].get(f"{sym}USD")
            price = float(s["closes"][k])
            if k < len(s["probs"]) and not np.isnan(s["probs"][k]):
                ml_prob = float(s["probs"][k])
            else:
                ml_prob = None
            if pos is None:
                reason = entry_block_reason(
                    cfg,
                    {"confidence": 1.0, "ml_prob_up": 1.0, "rl_position": 1.0},
                    exchange=ex,
                    global_positions=global_positions(),
                    exchange_positions=len(data[ex]["positions"]),
                    drawdown_pct=drawdown_pct,
                    daily_loss_pct=daily_loss_pct,
                    candle_is_new=True,
                )
                if reason:
                    block_counts[reason] += 1
                    continue
                reserve = 1000.0 * 0.30
                if float(data[ex]["cash_usd"]) <= reserve:
                    block_counts["cash_reserve"] += 1
                    continue
                an = qmb.record_and_analyze(
                    history[key], ml_prob,
                    (0.0 if sym in RL_ASSETS else None) if rl_block else None)
                if an["signal"] != "BUY_LONG" or float(an["confidence"]) < cfg.min_confidence:
                    continue
                if ml_prob is None or ml_prob < cfg.ml_min_prob_up:
                    block_counts["ml_not_confirmed"] += 1
                    continue
                rl = 0.0 if sym in RL_ASSETS else None
                if rl is not None and rl <= cfg.rl_veto_position:
                    block_counts["rl_veto"] += 1
                    continue
                investment = min(float(data[ex]["cash_usd"]) * 0.20, 200.0)
                if investment < 10.0:
                    block_counts["minimum_order"] += 1
                    continue
                entry_fee = investment * FEE
                exec_px = price * (1.0 + COST)
                qty = (investment - entry_fee) / exec_px
                data[ex]["cash_usd"] -= investment
                data[ex]["positions"][f"{sym}USD"] = {
                    "side": "LONG",
                    "entry_price": exec_px,
                    "entry_mid_price": price,
                    "qty": qty,
                    "invested_usd": investment,
                    "entry_fee_usd": round(entry_fee, 8),
                    "max_price_seen": price,
                    "opened_at": ts,
                    "mark_price": price,
                }
                data[ex]["entry_count"] += 1

        if ts % 3_600_000 == 0 and (ts // 3_600_000) % 24 == 0:
            equity_curve.append({"ts": ts, "equity": mark_equity()})

    # final mark-to-market
    for p in data.values():
        for pos in p["positions"].values():
            pos["open"] = True
    final_equity = mark_equity()
    return {
        "initial_total": initial_total,
        "final_equity": final_equity,
        "pnl": final_equity - initial_total,
        "trades": trades,
        "block_counts": dict(block_counts),
        "equity_curve": equity_curve,
        "open_positions": {f"{ex}:{sym}": v for ex, p in data.items()
                           for sym, v in p["positions"].items()},
    }


def summarize(r: dict, cfg) -> dict:
    tr = r["trades"]
    wins = [t for t in tr if t["net"] > 0]
    gw = sum(t["net"] for t in wins)
    gl = -sum(t["net"] for t in tr if t["net"] < 0)
    by_sym: Counter[str] = Counter()
    pnl_sym: dict[str, float] = defaultdict(float)
    for t in tr:
        by_sym[t["symbol"]] += 1
        pnl_sym[t["symbol"]] += t["net"]
    by_ex: Counter[str] = Counter()
    pnl_ex: dict[str, float] = defaultdict(float)
    for t in tr:
        by_ex[t["exchange"]] += 1
        pnl_ex[t["exchange"]] += t["net"]
    reasons = Counter(t["reason"] for t in tr)
    return {
        "n": len(tr),
        "wr": len(wins) / len(tr) * 100.0 if tr else 0.0,
        "pf": gw / gl if gl > 0 else float("inf"),
        "pnl": sum(t["net"] for t in tr),
        "avg_pct": statistics.mean(t["pct"] for t in tr) if tr else 0.0,
        "reasons": dict(reasons),
        "by_symbol": {s: (by_sym[s], round(pnl_sym[s], 2)) for s in by_sym},
        "by_exchange": {e: (by_ex[e], round(pnl_ex[e], 2)) for e in by_ex},
        "blocks": r["block_counts"],
        "final_equity": r["final_equity"],
        "total_pnl": r["pnl"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--output", type=Path, default=Path("data/reports/prod_3m_backtest.md"))
    args = ap.parse_args()

    env = load_unit_env()
    cfg = build_config(env)
    print("config: trail_ratio=%.3f tp=%.3f sl=%.3f ml_min=%.2f conf=%.2f dd=%.2f%% "
          "daily=%.2f%% exchanges=%s" % (
              cfg.trail_ratio, cfg.take_profit_pct, cfg.stop_loss_pct, cfg.ml_min_prob_up,
              cfg.min_confidence, cfg.max_drawdown_pct, cfg.max_daily_loss_pct,
              len(env.get("AIOS_QUANT_ALLOWED_EXCHANGES", "").split(","))), flush=True)

    series, used = load_series(env)
    print(f"series: {len(series)} (symbols: {len(set(s['symbol'] for s in series.values()))})", flush=True)

    from catboost import CatBoostClassifier

    model = CatBoostClassifier()
    model.load_model(str(qmb.MODELS_DIR / "catboost_price_dir_v2.cbm"))
    probs: dict[str, np.ndarray] = {}
    for key, s in series.items():
        X = s["feats"][qmb.FEATURES].values.astype(np.float64)
        probs[key] = model.predict_proba(X)[:, 1] if len(X) else np.array([])
        s["probs"] = probs[key]

    last_ts = max(int(s["times"][-1]) for s in series.values())
    from dateutil.relativedelta import relativedelta

    start_ms = int((datetime.fromtimestamp(last_ts / 1000, tz=UTC)
                    - relativedelta(months=args.months)).timestamp() * 1000)
    d0 = datetime.fromtimestamp(start_ms / 1000, tz=UTC).strftime("%Y-%m-%d")
    d1 = datetime.fromtimestamp(last_ts / 1000, tz=UTC).strftime("%Y-%m-%d")
    print(f"window: {d0} .. {d1}", flush=True)

    res = run_backtest(series, cfg, probs, start_ms)
    summ = summarize(res, cfg)

    # sensitivity: trailing priced at close (live engine prices at mid)
    res_c = run_backtest(series, cfg, probs, start_ms, trail_at_close=True)
    summ_c = summarize(res_c, cfg)

    # control: trail 0.988 (A/B legacy)
    cfg_ctl = build_config(env, trail_override=0.988)
    res_ctl = run_backtest(series, cfg_ctl, probs, start_ms)
    summ_ctl = summarize(res_ctl, cfg_ctl)

    # BTC buy&hold context
    btc_key = next((k for k, s in series.items() if s["symbol"] == "BTC"), None)
    bh = 0.0
    if btc_key:
        s = series[btc_key]
        i0 = int(np.searchsorted(s["times"], start_ms))
        bh = (float(s["closes"][-1]) / float(s["closes"][i0]) - 1.0) * 100.0

    def fmt(m):
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        return (f"n={m['n']} wr={m['wr']:.1f}% pf={pf} pnl={m['pnl']:+.2f}$ "
                f"(total {m['total_pnl']:+.2f}$)")

    print("MAIN  :", fmt(summ), flush=True)
    print("TRAIL@CLOSE:", fmt(summ_c), flush=True)
    print("CTL-0.988:", fmt(summ_ctl), flush=True)
    print("BTC buy&hold:", f"{bh:+.2f}%", flush=True)
    print("blocks:", summ["blocks"], flush=True)
    print("by_symbol:", summ["by_symbol"], flush=True)
    print("by_exchange:", summ["by_exchange"], flush=True)

    md = ["# Тестовый замер трейдинга: старт 3 месяца назад, текущая стратегия", "",
          f"Окно: **{d0} .. {d1}** | Конфиг: **из unit** `deploy/systemd/aios-quant-trading.service` "
          f"(trail_ratio={cfg.trail_ratio}, TP {cfg.take_profit_pct:.1%}, SL {cfg.stop_loss_pct:.1%}, "
          f"ML≥{cfg.ml_min_prob_up}, conf≥{cfg.min_confidence}, kill DD/daily {cfg.max_drawdown_pct:.2f}%)",
          "",
          "Методика: воспроизведение движка 1:1 (per-exchange $1000, reserve 30%, max $200/сделку, "
          "1 глобальная позиция, kill-свитчи от суммарного equity всех 10 бирж), цены — локальные "
          "1h OHLCV по всем разрешённым биржам (приоритет порядка в unit).",
          "",
          "| Прогон | Сделок | Winrate | PF | PnL закрытых $ | Итог equity $ |",
          "|---|---:|---:|---:|---:|---:|",
          f"| Текущая (trail={cfg.trail_ratio}) | {summ['n']} | {summ['wr']:.1f}% | "
          f"{summ['pf'] if summ['pf']==float('inf') else round(summ['pf'],2)} | {summ['pnl']:+.2f} | "
          f"{summ['final_equity']:.2f} |",
          f"| Sensitivity: trail-выход по close | {summ_c['n']} | {summ_c['wr']:.1f}% | "
          f"{summ_c['pf'] if summ_c['pf']==float('inf') else round(summ_c['pf'],2)} | {summ_c['pnl']:+.2f} | "
          f"{summ_c['final_equity']:.2f} |",
          f"| Контроль A/B: trail=0.988 | {summ_ctl['n']} | {summ_ctl['wr']:.1f}% | "
          f"{summ_ctl['pf'] if summ_ctl['pf']==float('inf') else round(summ_ctl['pf'],2)} | {summ_ctl['pnl']:+.2f} | "
          f"{summ_ctl['final_equity']:.2f} |",
          "",
          f"**BTC buy&hold за окно: {bh:+.2f}%** | Стартовый капитал: $1000 × 10 бирж = $10 000 "
          "(виртуально, используется ~1 позиция).",
          "",
          "## Блокировки входов (текущая стратегия)", "",
          "| Причина | Кол-во |", "|---|---:|"]
    for k, v in sorted(summ["blocks"].items(), key=lambda x: -x[1]):
        md.append(f"| {k} | {v} |")
    md += ["", "## Сделки (текущая стратегия)", "",
           "| # | Дата входа | Символ | Биржа | PnL $ | % | Причина | Держание ч |",
           "|---|---:|---|---:|---:|---:|---:|---:|"]
    for i, t in enumerate(sorted(res["trades"], key=lambda x: x["opened_at"]), 1):
        dt = datetime.fromtimestamp(t["opened_at"] / 1000, tz=UTC).strftime("%m-%d %H:%M")
        md.append(f"| {i} | {dt} | {t['symbol']} | {t['exchange']} | {t['net']:+.2f} | "
                  f"{t['pct']:+.2f} | {t['reason']} | {t['hold_h']} |")
    if not res["trades"]:
        md.append("| — | сделок нет | | | | | | |")
    md += ["", "## По символам и биржам", "",
           "| Символ | Сделок | PnL $ |", "|---|---:|---:|"]
    for s, (n, p) in sorted(summ["by_symbol"].items(), key=lambda x: x[1][1]):
        md.append(f"| {s} | {n} | {p:+.2f} |")
    md += ["", "| Биржа | Сделок | PnL $ |", "|---|---:|---:|"]
    for e, (n, p) in sorted(summ["by_exchange"].items(), key=lambda x: x[1][1]):
        md.append(f"| {e} | {n} | {p:+.2f} |")
    md += ["", "## Причины выхода", "", "| Причина | Кол-во |", "|---|---:|"]
    for k, v in sorted(summ["reasons"].items(), key=lambda x: -x[1]):
        md.append(f"| {k} | {v} |")
    md += ["",
           "**Допущения:** SL/TP/trailing по hi/lo бара (harness-конвенция); при trail=1.0 выход "
           "по пику — оптимистично, sensitivity по close — пессимистично; live-движок между ними. "
           "ML prob — catboost_price_dir_v2.cbm на 13 scale-free фичах; RL_ASSETS заблокированы "
           "(rl_veto, как в live: PPO FLAT). Сделки после окончания окна не маркируются."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    json.dump({"window": [d0, d1], "main": summ, "trail_close": summ_c, "control": summ_ctl,
               "btc_bh": bh}, open(str(args.output).replace(".md", ".json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
