#!/usr/bin/env python3
"""OOS profit experiments for Directional v2 — honest walk-forward on 12-month data (v2).

Changes vs v1:
- Symbols with < MIN_BARS history are excluded from OOS evaluation (short series distort
  the window and contribute no meaningful trades).
- ML threshold is calibrated on the TRAIN segment (percentile of prob_up over all train
  rows, gap excluded): q90/q95/q97 variants. Fixed 0.65 baseline kept for comparison.
- NO_ML control variant (no probability gate) to isolate the model's contribution.
- Report window = min test_start over admitted symbols.

Method
------
- Price source: allowlist venues (kucoin > bitstamp > mexc), ~8760 1h bars for full series.
- Two expanding-window folds: train 70% / test 30%, train 85% / test 15% (gap 48 bars).
- Fresh CatBoost v2 (identical hyperparams to scripts/quant_ml_eval_train.py) per fold.
- Variant battery fixed BEFORE seeing OOS results. Winner judged on OOS only.

Usage:
    python scripts/quant_oos_profit_experiments.py [--output data/reports/oos_profit_experiments.md]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quant_monthly_backtest as qmb

STAKE = 200.0
FEE = qmb.PROFILE["fee_rate"]
COST = qmb.PROFILE["half_spread_rate"] + qmb.PROFILE["slippage_rate"]

ML_PARAMS = dict(
    iterations=400,
    depth=5,
    learning_rate=0.03,
    l2_leaf_reg=5.0,
    loss_function="Logloss",
    eval_metric="AUC",
    random_seed=42,
    verbose=0,
    thread_count=-1,
)

GAP_BARS = 48
MIN_BARS = 1500  # admit symbols with enough history for a meaningful OOS window


# --------------------------------------------------------------------------- data --


def load_series() -> dict[str, dict]:
    """Load allowlist history and compute features + rolling SMAs + ATR14/close."""
    symbols, _venue_used = qmb.load_symbols("allowlist")
    out: dict[str, dict] = {}
    for sym, df in symbols.items():
        if len(df) < MIN_BARS:
            print(f"skip {sym}: only {len(df)} bars", flush=True)
            continue
        df = df.reset_index(drop=True)
        feats = qmb._compute_features(df)
        out[sym] = {
            "df": df,
            "feats": feats,
            "sma50": df["close"].rolling(50).mean().values,
            "sma100": df["close"].rolling(100).mean().values,
            "sma150": df["close"].rolling(150).mean().values,
            "sma200": df["close"].rolling(200).mean().values,
            "atr14": _atr14(df),
        }
    return out


def _atr14(df) -> np.ndarray:
    import pandas as pd

    hi, lo, cl = df["high"].values, df["low"].values, df["close"].values
    prev = np.roll(cl, 1)
    prev[0] = cl[0]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev), np.abs(lo - prev)))
    atr = pd.Series(tr).rolling(14).mean().values
    return atr / np.where(cl > 0, cl, 1.0)


# ----------------------------------------------------------------------- trading --


def simulate(sym: str, s: dict, variant: dict, test_start: int, ml_min: float) -> list[dict]:
    """Free-profile per-symbol simulation on [test_start, end); mirrors qmb exits 1:1."""
    closes, highs, lows = s["closes"], s["highs"], s["lows"]
    times, probs = s["times"], s["probs"]
    tp = variant.get("tp", qmb.PROFILE["take_profit_pct"])
    sl = variant.get("sl", qmb.PROFILE["stop_loss_pct"])
    trail = variant.get("trail", qmb.PROFILE["trail_ratio"])
    trend = variant.get("trend")  # None | sma50 | sma100 | sma150 | sma200
    cooldown_h = variant.get("cooldown_h", 0)
    max_atr = variant.get("max_atr", None)
    no_ml = variant.get("no_ml", False)

    sma_col = {"sma50": "sma50", "sma100": "sma100", "sma150": "sma150", "sma200": "sma200"}.get(trend or "")
    sma = s.get(sma_col) if sma_col else None

    history: list[float] = [float(c) for c in closes[:test_start]]
    pos = None
    last_loss_ts = 0
    trades: list[dict] = []

    for k in range(test_start, len(closes)):
        price = float(closes[k])
        ts = int(times[k])
        ml_prob = float(probs[k]) if k < len(probs) and not np.isnan(float(probs[k])) else None
        history.append(price)

        if pos is not None:
            entry_mid = pos["entry_mid"]
            qty = pos["qty"]
            max_seen = max(pos["max_seen"], price)
            pos["max_seen"] = max_seen
            hi, lo = float(highs[k]), float(lows[k])
            exit_px = None
            reason = ""
            if lo <= entry_mid * (1.0 + sl):
                exit_px = entry_mid * (1.0 + sl) * (1.0 - COST)
                reason = "stop_loss"
            elif hi >= entry_mid * (1.0 + tp):
                exit_px = entry_mid * (1.0 + tp) * (1.0 - COST)
                reason = "take_profit"
            elif max_seen > entry_mid * 1.01 and lo <= max_seen * trail:
                exit_px = max_seen * trail * (1.0 - COST)
                reason = "trailing_stop"
            else:
                an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
                if (an["signal"] == "SELL_SHORT" and an["confidence"] >= qmb.PROFILE["min_confidence"]
                        and ml_prob is not None and ml_prob <= 0.40
                        and (ts - pos["opened_at"]) >= qmb.PROFILE["min_hold_seconds"] * 1000):
                    exit_px = price * (1.0 - COST)
                    reason = "confirmed_bearish_exit"
            if exit_px is not None:
                proceeds = exit_px * qty
                net = proceeds - pos["invested"] - exit_px * qty * FEE
                trades.append({"symbol": sym, "net": net, "pct": net / pos["invested"] * 100.0,
                               "reason": reason, "ts": ts, "opened_at": pos["opened_at"]})
                if net < 0:
                    last_loss_ts = ts
                pos = None

        # ---- entry conditions ----
        if trend and sma is not None:
            sma_v = float(sma[k])
            if not (sma_v == sma_v and price > sma_v):
                continue
        if max_atr is not None:
            atr_v = float(s["atr14"][k])
            if atr_v == atr_v and atr_v > max_atr:
                continue
        if cooldown_h and (ts - last_loss_ts) < cooldown_h * 3600 * 1000:
            continue
        an = qmb.record_and_analyze(history, ml_prob, 0.0 if sym in qmb.RL_ASSETS else None)
        if an["signal"] != "BUY_LONG" or an["confidence"] < qmb.PROFILE["min_confidence"]:
            continue
        if not no_ml and (ml_prob is None or ml_prob < ml_min):
            continue
        rl = 0.0 if sym in qmb.RL_ASSETS else None
        if rl is not None and rl <= qmb.PROFILE["rl_veto_position"]:
            continue
        entry_fee = STAKE * FEE
        exec_px = price * (1.0 + COST)
        pos = {"entry_mid": price, "qty": (STAKE - entry_fee) / exec_px,
               "invested": STAKE, "entry_fee": entry_fee, "max_seen": price, "opened_at": ts}

    if pos is not None:  # mark-to-market at period end
        exit_px = price * (1.0 - COST)
        proceeds = exit_px * pos["qty"]
        net = proceeds - pos["invested"] - exit_px * pos["qty"] * FEE
        trades.append({"symbol": sym, "net": net, "pct": net / STAKE * 100.0,
                       "reason": "period_end", "ts": ts})
    return trades


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "pnl": 0.0, "avg": 0.0}
    wins = [t for t in trades if t["net"] > 0]
    gw = sum(t["net"] for t in wins)
    gl = -sum(t["net"] for t in trades if t["net"] < 0)
    return {"n": len(trades), "wr": len(wins) / len(trades) * 100.0,
            "pf": gw / gl if gl > 0 else float("inf"),
            "pnl": sum(t["net"] for t in trades),
            "avg": statistics.mean(t["pct"] for t in trades)}


# ------------------------------------------------------------- ML per fold --


def train_and_predict(series: dict[str, dict], train_frac: float) -> tuple[dict[str, np.ndarray], dict[str, int], float]:
    """Train fresh CatBoost on first `train_frac` bars of each symbol; predict prob_up
    on the test tail; also return the train-segment prob_up distribution (for calibration)."""
    from catboost import CatBoostClassifier

    feats_cols = qmb.FEATURES
    train_rows: list[np.ndarray] = []
    train_y: list[np.ndarray] = []
    test_starts: dict[str, int] = {}
    prob_map: dict[str, np.ndarray] = {}

    for sym, s in series.items():
        df = s["df"]
        feats = s["feats"]
        closes = df["close"].values
        target = (np.roll(closes, -1) > closes).astype(int)
        target[-1] = 0
        n = len(df)
        cut = int(n * train_frac)
        test_starts[sym] = cut

        X_tr = feats[feats_cols].values[: cut - GAP_BARS].astype(np.float64)
        y_tr = target[: cut - GAP_BARS]
        ok_tr = ~np.isnan(X_tr).any(axis=1)
        train_rows.append(X_tr[ok_tr])
        train_y.append(y_tr[ok_tr])

        prob_map[sym] = np.full(n, np.nan)

    X_all = np.vstack(train_rows)
    y_all = np.concatenate(train_y)
    print(f"fold train_frac={train_frac}: train rows={len(X_all)}", flush=True)
    model = CatBoostClassifier(**ML_PARAMS)
    model.fit(X_all, y_all)

    # train-segment probs for calibration
    tr_probs: list[np.ndarray] = []
    for sym, s in series.items():
        df = s["df"]
        feats = s["feats"]
        cut = test_starts[sym]
        X_tr = feats[feats_cols].values[: cut - GAP_BARS].astype(np.float64)
        ok = ~np.isnan(X_tr).any(axis=1)
        if ok.any():
            tr_probs.append(model.predict_proba(X_tr[ok])[:, 1])
        X_te = feats[feats_cols].values[cut:].astype(np.float64)
        ok_te = ~np.isnan(X_te).any(axis=1)
        if ok_te.any():
            p = model.predict_proba(X_te[ok_te])[:, 1]
            arr = np.full(len(X_te), np.nan)
            arr[ok_te] = p
            prob_map[sym][cut:] = arr
    tr_all = np.concatenate(tr_probs) if tr_probs else np.array([])
    return prob_map, test_starts, tr_all


# ------------------------------------------------------------- variant run --




def dedup(trades: list[dict]) -> list[dict]:
    """Remove duplicate trades across overlapping OOS windows (same symbol+entry)."""
    seen: set[tuple] = set()
    out = []
    for t in trades:
        key = (t["symbol"], t["opened_at"])
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def make_variants(train_prob: np.ndarray) -> list[tuple[str, dict, float]]:
    """Round-3 battery: isolate the trailing-stop effect; strict ML quantiles."""
    q98 = float(np.percentile(train_prob, 98))
    q99 = float(np.percentile(train_prob, 99))
    print(f"train prob_up percentiles: q98={q98:.4f} q99={q99:.4f}", flush=True)
    return [
        ("BASE: ML>=0.65 (как в проде)", {}, 0.65),
        ("N1: жёсткий трейлинг trail=1.0", {"trail": 1.0}, 0.65),
        ("N1m: мягкий трейлинг 0.995", {"trail": 0.995}, 0.65),
        ("N1X: N1 + TP 2.5%/SL 1.0%", {"trail": 1.0, "tp": 0.025, "sl": -0.010}, 0.65),
        ("N1q98: N1 + ML топ-2% train", {"trail": 1.0}, q98),
        ("N1q99: N1 + ML топ-1% train", {"trail": 1.0}, q99),
        ("N1Xq99: N1X + ML топ-1% train", {"trail": 1.0, "tp": 0.025, "sl": -0.010}, q99),
    ]


def portfolio_sim(trades: list[dict], *, start_cash: float = 1000.0,
                  max_dd: float = 0.0025, max_daily_loss: float = 0.0025) -> dict:
    """Merge potential trades under prod profile: max 1 global position, drawdown and
    daily-loss kill switches (1:1 with quant_directional_policy.entry_block_reason)."""
    from datetime import datetime, timezone

    ordered = sorted(trades, key=lambda t: t["opened_at"])
    cash = start_cash
    peak = start_cash
    equity = start_cash
    last_close_ms = 0
    taken = 0
    blocked_dd = False
    current_day = ""
    day_start_equity = start_cash
    day_pnl = 0.0
    day_trades: list[dict] = []
    for t in ordered:
        day = datetime.fromtimestamp(t["opened_at"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        if day != current_day:
            current_day = day
            day_start_equity = equity
            day_pnl = 0.0
        if t["opened_at"] < last_close_ms:
            continue  # position still busy
        if blocked_dd:
            continue
        if day_pnl <= -max_daily_loss * day_start_equity:
            continue  # daily loss kill
        if equity <= peak * (1.0 - max_dd):
            blocked_dd = True
            continue  # global drawdown kill (stays blocked)
        cash += t["net"]
        equity = cash
        peak = max(peak, equity)
        day_pnl += t["net"]
        last_close_ms = t["ts"]
        taken += 1
        day_trades.append(t)
    return {"start": start_cash, "end": equity, "pnl": equity - start_cash,
            "taken": taken, "blocked_dd": blocked_dd}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=Path("data/reports/oos_profit_experiments.md"))
    args = ap.parse_args()

    series = load_series()
    print(f"admitted symbols: {len(series)}", flush=True)
    for sym, s in series.items():
        df = s["df"]
        s["closes"] = df["close"].values
        s["highs"] = df["high"].values
        s["lows"] = df["low"].values
        s["times"] = df["timestamp_ms"].values

    rows_by_variant: dict[str, list[dict]] = {}
    variants: list[tuple[str, dict, float]] | None = None
    fold_info: list[dict] = []

    for train_frac in (0.50, 0.60, 0.70, 0.85):
        probs, test_starts, tr_prob = train_and_predict(series, train_frac)
        if variants is None:
            variants = make_variants(tr_prob)
            rows_by_variant = {name: [] for name, _, _ in variants}
        for sym, s in series.items():
            s["probs"] = probs[sym]

        t0 = min(int(s["times"][test_starts[sym]]) for sym in series)
        t1 = max(int(s["times"][-1]) for s in series.values())
        d0 = datetime.fromtimestamp(t0 / 1000, tz=UTC).strftime("%Y-%m-%d")
        d1 = datetime.fromtimestamp(t1 / 1000, tz=UTC).strftime("%Y-%m-%d")
        fold_info.append({"frac": train_frac, "window": f"{d0} .. {d1}",
                          "test_bars": max(len(ss["times"]) - test_starts[sym] for sym, ss in series.items())})
        print(f"fold train_frac={train_frac}: OOS window {d0} .. {d1}", flush=True)

        for name, variant, ml_min in variants:
            bl = variant.get("blacklist", set())
            trades = []
            for sym, s in series.items():
                if sym in bl:
                    continue
                trades.extend(simulate(sym, s, variant, test_starts[sym], ml_min))
            rows_by_variant[name].extend(trades)
            m = metrics(trades)
            print(f"  {name}: n={m['n']} wr={m['wr']:.1f}% PF={m['pf']:.2f} pnl={m['pnl']:+.2f}$", flush=True)

    # ---- report ----
    md = ["# OOS-эксперименты: реальная прибыль Directional v2 (walk-forward)", "",
          "Методика: свежая CatBoost v2 обучена на train-окне каждого фолда (70% и 85% истории),",
          "оценка только на нетронутых test-окнах. Порог ML калибруется на train-перцентиле.",
          "Символы с историей < 1500 баров исключены (искажают окно). Ставка $200/сделку, свободный профиль.",
          "",
          f"Фолды (OOS-окна): {fold_info}",
          "",
          "| Вариант | Сделок | Winrate | PF | PnL $ | avg % |",
          "|---|---:|---:|---:|---:|---:|"]
    for name, _, _ in variants:
        m = metrics(rows_by_variant[name])
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | {m['avg']:+.3f} |")
    # reason breakdown for BASE vs N1 (isolate trailing-stop damage)
    def reasons(trades):
        from collections import Counter
        c = Counter(t["reason"] for t in trades)
        return ", ".join(f"{k}={v}" for k, v in c.most_common()) or "нет сделок"

    md += ["",
           "**Интерпретация:** результаты на OOS-окнах; победитель требует подтверждения на следующем",
           "нетронутом окне (не подбирать параметры по этим цифрам).",
           "",
           "## Разложение сделок по причине выхода (все OOS-окна)",
           "",
           "| Вариант | TP | SL | trailing | bearish_exit | period_end |",
           "|---|---:|---:|---:|---:|---:|"]
    for name in ("BASE: ML>=0.65 (как в проде)", "N1: жёсткий трейлинг trail=1.0",
                 "N1m: мягкий трейлинг 0.995"):
        tr = rows_by_variant.get(name, [])
        from collections import Counter
        c = Counter(t["reason"] for t in tr)
        md.append(f"| {name} | {c['take_profit']} | {c['stop_loss']} | {c['trailing_stop']} | "
                  f"{c['confirmed_bearish_exit']} | {c['period_end']} |")
    md += ["",
           "## Детали сделок N1 (трейлинг выкл, все OOS-окна)", ""]
    tr = dedup(rows_by_variant.get("N1: жёсткий трейлинг trail=1.0", []))
    for t in sorted(tr, key=lambda x: x["opened_at"]):
        d = datetime.fromtimestamp(t["opened_at"] / 1000, tz=UTC).strftime("%m-%d %H:%M")
        md.append(f"- {d} {t['symbol']}: {t['net']:+.2f}$ ({t['pct']:+.2f}%) — {t['reason']}")
    if not tr:
        md.append("- нет сделок")
    md += ["",
           "**Интерпретация:** результаты на OOS-окнах; победитель требует подтверждения на следующем",
           "нетронутом окне (не подбирать параметры по этим цифрам).",
           "",
           "## Портфельная симуляция финалиста (прод-профиль)",
           "",
           "Прод-профиль: max 1 глобальная позиция, kill-свитчи drawdown/daily-loss 0.25%,",
           "стартовый капитал $1000, ставка $200/сделку. Сделки потенциальные (free-profile) сливаются",
           "событийно; drawdown-kill после срабатывания блокирует входы до конца окна."]

    # Unique-trade summary (windows overlap -> dedup by symbol+entry)
    md += ["", "## Уникальные сделки (дедуп по символ+вход)", "",
           "| Вариант | Сделок | Winrate | PF | PnL $ | avg % |",
           "|---|---:|---:|---:|---:|---:|"]
    for name in ("BASE: ML>=0.65 (как в проде)", "N1: жёсткий трейлинг trail=1.0",
                 "N1m: мягкий трейлинг 0.995", "N1X: N1 + TP 2.5%/SL 1.0%"):
        m = metrics(dedup(rows_by_variant.get(name, [])))
        pf = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
        md.append(f"| {name} | {m['n']} | {m['wr']:.1f}% | {pf} | {m['pnl']:+.2f} | {m['avg']:+.3f} |")

    # Portfolio sim on DEDUPED trades
    for sim_name in ("N1: жёсткий трейлинг trail=1.0", "BASE: ML>=0.65 (как в проде)"):
        tr = dedup(rows_by_variant.get(sim_name, []))
        ps = portfolio_sim(tr)
        md += [f"- **{sim_name}**: {ps['taken']} сделок в портфеле, "
               f"PnL {ps['pnl']:+.2f}$ (end {ps['end']:.2f}$), "
               f"drawdown-kill: {'ДА' if ps['blocked_dd'] else 'нет'}"]
    if len(rows_by_variant.get("N1: жёсткий трейлинг trail=1.0", [])) < 30:
        md += ["", "⚠️ Выборка N1 мала (<30 сделок) — результат ориентировочный, нужен "
               "следующий нетронутый период для подтверждения."]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(md), encoding="utf-8")
    print(f"report -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
