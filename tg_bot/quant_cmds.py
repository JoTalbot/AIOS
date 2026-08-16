#!/usr/bin/env python3
"""/quant command for the Telegram bot: status of all quant/portfolio services.

Reads runtime state files and service statuses; returns a compact HTML summary.
Kept OUTSIDE run_telegram_bot.py (protected) so the bot file needs only a thin
wrapper + dispatch branch.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path("/root/AIOS")


def _fmt_num(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def cmd_quant() -> str:
    lines = ["📊 <b>Quant-контуры</b>", ""]

    # MM-сигналы: точность
    try:
        r = subprocess.run(["/opt/aios/.venv/bin/python", "scripts/mm_signal_score.py"],
                           capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        out = [l for l in r.stdout.strip().split("\n") if l and "эмиссий" not in l]
        if out:
            lines.append("📡 <b>MM-сигналы:</b>")
            lines.extend(f"  {l}" for l in out)
        else:
            lines.append("📡 MM-сигналы: нет данных")
    except Exception as e:
        lines.append(f"📡 MM: ошибка ({e})")

    # ws-данные
    try:
        con = sqlite3.connect(str(ROOT / "data/quant/orderbooks.sqlite"))
        n = con.execute("SELECT COUNT(*) FROM snapshots_ws").fetchone()[0]
        h = (con.execute("SELECT MAX(ts)-MIN(ts) FROM snapshots_ws").fetchone()[0] or 0) / 3600
        nt = con.execute("SELECT COUNT(*) FROM trades_ws").fetchone()[0]
        con.close()
        lines.append(f"🌊 <b>ws-данные:</b> {_fmt_num(n)} снапшотов ({h:.1f} ч), "
                     f"trade-flow {_fmt_num(nt)} записей")
    except Exception as e:
        lines.append(f"🌊 ws: ошибка ({e})")

    # DCA
    try:
        s = json.loads((ROOT / "data/dca_paper_state.json").read_text())
        vlog = [json.loads(l) for l in
                (ROOT / "data/dca_paper_value.jsonl").read_text().splitlines() if l]
        val = vlog[-1]["value_usd"] if vlog else 0.0
        dep = float(s.get("deposited_usd", 0))
        pnl = val - dep
        pct = pnl / dep * 100 if dep else 0
        lines.append(f"📈 <b>DCA:</b> ${dep:.0f} → ${val:.2f} ({pnl:+.2f}$ / {pct:+.1f}%)")
    except Exception as e:
        lines.append(f"📈 DCA: ошибка ({e})")

    # A/B paper
    try:
        m = json.loads((ROOT / "data/multi_exchange_portfolios_owner_paper.json").read_text())
        c = json.loads((ROOT / "data/multi_exchange_portfolios_owner_paper_control.json").read_text())
        tm = sum(p.get("total_trades", 0) for p in m.values() if isinstance(p, dict))
        tc = sum(p.get("total_trades", 0) for p in c.values() if isinstance(p, dict))
        lines.append(f"⚖️ <b>A/B:</b> main (trail 1.0) {tm} | control (0.988) {tc} сделок")
    except Exception as e:
        lines.append(f"⚖️ A/B: ошибка ({e})")

    # новостной сентимент
    try:
        import json as _j
        rows = [_j.loads(l) for l in
                (ROOT / "data" / "quant" / "news_sentiment.jsonl").read_text().splitlines() if l]
        if rows:
            pos = sum(1 for r in rows if r["sentiment"] > 0.2)
            neg = sum(1 for r in rows if r["sentiment"] < -0.2)
            last = rows[-1]
            avg = sum(r["sentiment"] for r in rows[-50:]) / max(1, len(rows[-50:]))
            lines.append(f"📰 <b>Сентимент:</b> {len(rows)} новостей (pos {pos} / neg {neg}), "
                         f"avg(50) {avg:+.2f}, последняя {last['label']}")
    except Exception:
        pass
    # Fear & Greed
    try:
        import json as _j
        ctx = _j.loads((ROOT / "data" / "quant" / "market_context_latest.json").read_text())
        fng = ctx.get("fng", {})
        if fng.get("value") is not None:
            lines.append(f"😨 <b>Fear&Greed:</b> {fng['value']} ({fng['class']})")
    except Exception:
        pass
    # T2 momentum
    try:
        import json as _j
        st = _j.loads((ROOT / "data" / "t2_paper_state.json").read_text())
        eq = float(st.get("equity", 0))
        bh = float(st.get("cash_equiv", 0))
        pct = (eq / 10000 - 1) * 100 if eq else 0
        lines.append(f"📈 <b>T2 (SMA50):</b> {st.get('position')} | equity ${eq:,.0f} "
                     f"({pct:+.1f}%) | BH ${bh:,.0f} | сделок {len(st.get('trades', []))}")
    except Exception:
        pass
    # funding/OI
    try:
        fdir = ROOT / "data/quant/funding_oi"
        days = len(list(fdir.glob("daily_BTC.jsonl")))
        if days:
            lines.append(f"💧 <b>Funding/OI:</b> {days} дн истории")
    except Exception:
        pass

    # сервисы
    try:
        svc = subprocess.run(
            ["systemctl", "is-active",
             "aios-orderbook-ws.service", "aios-mm-signal-monitor.timer",
             "aios-mm-signal-emitter.timer", "aios-dca-paper.timer",
             "aios-funding-oi-daily.timer", "aios-quant-trading.service",
             "aios-quant-trading-control.service"],
            capture_output=True, text=True, timeout=30)
        st = svc.stdout.strip().split("\n")
        lines.append(f"🖥 <b>Сервисы:</b> {', '.join(st)}")
    except Exception as e:
        lines.append(f"🖥 сервисы: ошибка ({e})")

    return "\n".join(lines)
