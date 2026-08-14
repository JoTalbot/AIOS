#!/usr/bin/env python3
"""Generate read-only quant monitoring signals; never places orders."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_core.quant_regime_v3 import compute_regime_features

PREFERRED = ("kraken", "binance", "kucoin", "bitstamp", "mexc")


def _json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _latest_rows(data_root: Path, symbol: str, limit: int = 150, *, now_ms: float | None = None):
    # Pick the most complete FRESH series among preferred exchanges: a long but
    # stale series (e.g. delisted pair on one venue) must not shadow a shorter
    # live one. Tie-break by preference order (strict > keeps it).
    if now_ms is None:
        from datetime import datetime, timezone

        now_ms = datetime.now(timezone.utc).timestamp() * 1000.0
    staleness_ms = 2 * 3_600_000.0  # 2h
    best_len = -1
    best_exchange = ""
    best_rows: list[dict] = []
    for exchange in PREFERRED:
        path = data_root / symbol / exchange / f"{symbol}_1h.csv"
        if not path.exists():
            continue
        try:
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
        except OSError:
            continue
        if not rows:
            continue
        try:
            last_ts = float(rows[-1]["timestamp_ms"])
        except (KeyError, ValueError):
            continue
        if now_ms - last_ts > staleness_ms:
            continue  # stale series — skip
        if len(rows) > best_len:
            best_len = len(rows)
            best_exchange = exchange
            best_rows = rows
    if not best_rows:
        return "", []
    best_rows = best_rows[-limit:]
    return best_exchange, [
        {
            "timestamp": float(row["timestamp_ms"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for row in best_rows
    ]


def build_report(data_root: Path, ml_path: Path, rl_path: Path, *, now_ms: float) -> dict:
    ml = _json(ml_path, {}).get("signals", [])
    rl = _json(rl_path, {}).get("signals", [])
    ml_by = {str(item.get("symbol", "")).upper(): item for item in ml}
    rl_by = {str(item.get("asset", "")).upper(): item for item in rl}
    signals = []
    symbols = sorted(set(ml_by) | set(rl_by))
    for symbol in symbols:
        exchange, rows = _latest_rows(data_root, symbol, now_ms=now_ms)
        if not rows:
            continue
        # Последний бар может быть ещё не закрыт (частичный объём -> ложный
        # "illiquid"); regime считаем по последнему закрытому бару.
        feature = compute_regime_features(rows)[-2] if len(rows) >= 2 else compute_regime_features(rows)[-1]
        age_hours = max(0.0, (now_ms - rows[-1]["timestamp"]) / 3_600_000.0)
        prob = float(ml_by.get(symbol, {}).get("prob_up", 0.5) or 0.5)
        position = float(rl_by.get(symbol, {}).get("position", 0.5) or 0.5)
        regime = str(feature["regime"])
        if age_hours > 2 or regime == "illiquid":
            label = "NO_DATA"
        elif regime == "trend_up" and prob >= 0.60 and position > 0.30:
            label = "WATCH_UP"
        elif regime == "trend_down" and prob <= 0.40:
            label = "WATCH_DOWN"
        else:
            label = "NEUTRAL"
        confidence = min(1.0, abs(prob - 0.5) * 2.0 + abs(position - 0.5) * 0.5)
        signals.append(
            {
                "symbol": symbol,
                "exchange": exchange,
                "label": label,
                "confidence": round(confidence, 4),
                "regime": regime,
                "ml_prob_up": round(prob, 4),
                "rl_position": round(position, 4),
                "last_price": rows[-1]["close"],
                "age_hours": round(age_hours, 3),
                "atr_percentile": round(float(feature["atr_percentile"]), 4),
                "volume_percentile": round(float(feature["volume_percentile"]), 4),
            }
        )
    counts = {
        label: sum(item["label"] == label for item in signals)
        for label in ("WATCH_UP", "WATCH_DOWN", "NEUTRAL", "NO_DATA")
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "product": "aios_quant_signal_monitor",
        "execution": "read_only",
        "trading_entry_mode": "freeze",
        "counts": counts,
        "signals": sorted(signals, key=lambda item: (-item["confidence"], item["symbol"])),
    }


def markdown(report: dict) -> str:
    lines = [
        "# AIOS Quant Signal Monitor",
        "",
        "> Read-only monitoring; не является командой на сделку.",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "| Asset | Label | Regime | ML | RL | Freshness |",
        "|---|---|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {x['symbol']} | {x['label']} | {x['regime']} | {x['ml_prob_up']:.3f} | {x['rl_position']:.3f} | {x['age_hours']:.1f}h |"
        for x in report["signals"]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/quant"))
    parser.add_argument("--json-output", type=Path, default=Path("data/reports/quant_signal_product.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("data/reports/quant_signal_product.md"))
    args = parser.parse_args()
    report = build_report(
        args.data_root,
        args.data_root / "ml_signals.json",
        args.data_root / "rl_signals.json",
        now_ms=datetime.now(UTC).timestamp() * 1000,
    )
    for path, content in (
        (args.json_output, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
        (args.markdown_output, markdown(report)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(content, encoding="utf-8")
        temp.replace(path)
    print(f"signals={len(report['signals'])} counts={report['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
