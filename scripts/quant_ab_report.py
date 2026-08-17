#!/usr/bin/env python3
"""Weekly A/B report for the Directional-v2 paper experiment.

Compares the owner paper portfolios:
  main    (multi_exchange_portfolios_owner_paper.json,         trail=1.0)
  control (multi_exchange_portfolios_owner_paper_control.json, trail=0.988)

Read-only. Writes data/reports/quant_ab_report.json and, with --notify,
sends a short digest to the owner's Telegram.

Usage:
    python scripts/quant_ab_report.py [--notify]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MAIN = REPO_ROOT / "data" / "multi_exchange_portfolios_owner_paper.json"
CONTROL = REPO_ROOT / "data" / "multi_exchange_portfolios_owner_paper_control.json"
OUT = REPO_ROOT / "data" / "reports" / "quant_ab_report.json"


def _portfolio_stats(data: dict) -> dict:
    """Aggregate paper metrics across exchange portfolios."""

    exchanges = [v for k, v in data.items() if k not in {"cross_arbitrage", "_risk_state"}]
    closed = sum(int(v.get("closed_trades", 0) or 0) for v in exchanges)
    wins = sum(int(v.get("winning_trades", 0) or 0) for v in exchanges)
    realized = sum(float(v.get("realized_pnl_usd", 0.0) or 0.0) for v in exchanges)
    gross = sum(float(v.get("gross_pnl_usd", 0.0) or 0.0) for v in exchanges)
    fees = sum(float(v.get("fees_paid_usd", 0.0) or 0.0) for v in exchanges)
    exec_costs = sum(float(v.get("execution_costs_usd", 0.0) or 0.0) for v in exchanges)
    net_profit = sum(float(v.get("net_profit_usd", 0.0) or 0.0) for v in exchanges)
    net_loss = sum(float(v.get("net_loss_usd", 0.0) or 0.0) for v in exchanges)
    risk = data.get("_risk_state") or {}
    return {
        "closed_trades": closed,
        "winning_trades": wins,
        "win_rate_pct": round(100.0 * wins / closed, 1) if closed else None,
        "realized_pnl_usd": round(realized, 4),
        "gross_pnl_usd": round(gross, 4),
        "fees_usd": round(fees, 4),
        "execution_costs_usd": round(exec_costs, 4),
        "profit_factor": round(net_profit / net_loss, 3) if net_loss > 0 else None,
        "equity_usd": round(float(risk.get("equity_usd", 0.0) or 0.0), 2),
        "max_drawdown_pct_seen": round(float(risk.get("max_drawdown_pct_seen", 0.0) or 0.0), 4),
        "entry_mode": risk.get("entry_mode"),
    }


def compare_portfolios(main: dict, control: dict) -> dict:
    """Pure A/B comparison (unit-tested)."""

    return {"main": _portfolio_stats(main), "control": _portfolio_stats(control)}


def _env(key: str) -> str:
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    v = os.environ.get(key, "")
    if v:
        return v
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("⚠️ telegram credentials not found; skip notify")
        return False
    payload = {"chat_id": int(chat), "text": html.escape(text)[:3900],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60):
            return True
    except Exception:
        return False


def _fmt_side(name: str, s: dict) -> str:
    lines = [f"{name}:"]
    lines.append(f"  сделки: {s['closed_trades']} (win {s['win_rate_pct']}%)" if s["win_rate_pct"] is not None
                 else f"  сделки: {s['closed_trades']}")
    lines.append(f"  realized PnL: {s['realized_pnl_usd']:+.4f} USD | gross {s['gross_pnl_usd']:+.4f} | fees {s['fees_usd']:.4f}")
    lines.append(f"  exec costs: {s['execution_costs_usd']:.4f} | PF: {s['profit_factor']} | equity: {s['equity_usd']}")
    lines.append(f"  max DD seen: {s['max_drawdown_pct_seen']:.3f}% | mode: {s['entry_mode']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notify", action="store_true", help="send the digest to Telegram")
    args = parser.parse_args()

    if not MAIN.exists() or not CONTROL.exists():
        print("SKIP: portfolio files missing")
        return 0
    main_data = json.loads(MAIN.read_text(encoding="utf-8"))
    control_data = json.loads(CONTROL.read_text(encoding="utf-8"))
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "comparison": compare_portfolios(main_data, control_data),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    c = report["comparison"]
    text = (
        "📊 <b>Directional v2 A/B paper</b> (main trail=1.0 vs control 0.988)\n"
        + _fmt_side("🅰️ main", c["main"]) + "\n"
        + _fmt_side("🅱️ control", c["control"]) + "\n"
        + "Полные данные: data/reports/quant_ab_report.json"
    )
    print(text.replace("<b>", "").replace("</b>", ""))
    if args.notify:
        print("notified:", _tg(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
