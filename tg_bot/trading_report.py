#!/usr/bin/env python3
"""Detailed trading report for the 'Трейдинг' Telegram button.

Gathers every paper portfolio (Directional v2 A/B, DCA VA+control, basket
top-10 vol-targeting, T2 momentum 5 legs + portfolio, freqtrade T2 dry),
market-microstructure status (ws snapshots/latency, queue model), scoreboard
verdict and service health; formats compact HTML chunks (Telegram 4096 limit)
and, separately, produces an LLM analytics + scenario-forecast section via
LLMBalancer (read-only, paper-only, with explicit honesty framing: no
financial advice).

Kept OUTSIDE protected files; callbacks.py wires one branch.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/root/AIOS")

MAX_CHUNK = 3800

SERVICES = (
    "aios-quant-trading", "aios-quant-trading-control", "aios-orderbook-ws",
    "aios-orderbook-research", "aios-freqtrade-t2-dry", "aios-market-data",
    "aios-quant-ml-inference", "aios-dca-paper.timer",
    "aios-basket-paper.timer", "aios-strategy-scoreboard.timer",
)


# --------------------------------------------------------------- helpers ----
def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _fmt_usd(v: float) -> str:
    return f"{v:+,.2f}$"


def _chunks(text: str, limit: int = MAX_CHUNK) -> list[str]:
    """Split text into Telegram-safe chunks on line boundaries."""

    if len(text) <= limit:
        return [text]
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:]
    if text:
        parts.append(text)
    return parts


# --------------------------------------------------------------- snapshots --
def snap_directional() -> dict:
    out = {"arms": {}, "ok": False}
    for tag, fname in (("main", "multi_exchange_portfolios_owner_paper.json"),
                       ("control", "multi_exchange_portfolios_owner_paper_control.json")):
        data = _read_json(ROOT / "data" / fname, {})
        if not isinstance(data, dict) or not data:
            continue
        exchanges = [v for k, v in data.items()
                     if k not in ("cross_arbitrage", "_risk_state") and isinstance(v, dict)]
        closed = sum(int(v.get("closed_trades", 0) or 0) for v in exchanges)
        wins = sum(int(v.get("winning_trades", 0) or 0) for v in exchanges)
        realized = sum(float(v.get("realized_pnl_usd", 0.0) or 0.0) for v in exchanges)
        gross = sum(float(v.get("gross_pnl_usd", 0.0) or 0.0) for v in exchanges)
        fees = sum(float(v.get("fees_paid_usd", 0.0) or 0.0) for v in exchanges)
        positions = [(ex, pos) for ex, v in zip(
            [k for k, v2 in data.items() if k not in ("cross_arbitrage", "_risk_state")],
            exchanges) for pos in (v.get("positions") or {}).values() if pos]
        trade_log = [t for v in exchanges for t in (v.get("trade_log") or [])]
        risk = data.get("_risk_state") or {}
        out["arms"][tag] = {
            "closed": closed, "wins": wins, "realized": realized, "gross": gross,
            "fees": fees,
            "win_rate": round(100 * wins / closed, 1) if closed else None,
            "open_positions": len(positions),
            "equity": round(float(risk.get("equity_usd", 0.0) or 0.0), 2),
            "dd_pct": round(float(risk.get("max_drawdown_pct_seen", 0.0) or 0.0), 4),
            "entry_mode": risk.get("entry_mode", "?"),
            "recent_trades": trade_log[-5:],
        }
    out["ok"] = bool(out["arms"])
    return out


def snap_dca() -> dict:
    out = {}
    for tag, cfg_f, state_f, hist_f in (
        ("VA main", "dca_portfolio.json", "dca_paper_state.json", "dca_paper_value.jsonl"),
        ("control", "dca_portfolio_control.json", "dca_paper_state_control.json",
         "dca_paper_value_control.jsonl"),
    ):
        state = _read_json(ROOT / "data" / state_f, {})
        cfg = _read_json(ROOT / "data" / cfg_f, {})
        hist_path = ROOT / "data" / hist_f
        rows = []
        if hist_path.exists():
            rows = [json.loads(l) for l in hist_path.read_text(encoding="utf-8").splitlines() if l]
        last = rows[-1] if rows else None
        out[tag] = {
            "mode": cfg.get("mode", state.get("mode", "?")),
            "weekly": cfg.get("weekly_amount_usd", state.get("weekly_amount_usd")),
            "value": last.get("value_usd") if last else None,
            "deposited": last.get("deposited_usd") if last else None,
            "fees": last.get("fees_usd") if last else None,
            "date": last.get("date") if last else None,
        }
    return out


def snap_basket() -> dict:
    state = _read_json(ROOT / "data" / "reports" / "basket_paper_state.json", {})
    hist_path = ROOT / "data" / "reports" / "basket_paper.jsonl"
    rows = []
    if hist_path.exists():
        rows = [json.loads(l) for l in hist_path.read_text(encoding="utf-8").splitlines() if l]
    last = rows[-1] if rows else None
    return {
        "value": last.get("value_usd") if last else None,
        "pnl_pct": last.get("pnl_pct") if last else None,
        "invested": last.get("invested_usd") if last else None,
        "fees": last.get("fees_paid_usd") if last else None,
        "date": last.get("day") if last else None,
        "weights_rule": state.get("weights_rule", "?"),
        "cash": round(float(state.get("cash_usd", 0.0) or 0.0), 2) if state else None,
    }


def snap_t2() -> dict:
    legs = {}
    for tag, fname in (("BTC", "t2_paper_state.json"), ("ETH", "t2_paper_state_ethusd.json"),
                       ("SOL", "t2_paper_state_solusd.json"), ("BNB", "t2_paper_state_bnbusd.json"),
                       ("NEAR", "t2_paper_state_nearusd.json")):
        st = _read_json(ROOT / "data" / fname, {})
        if st:
            legs[tag] = {
                "position": st.get("position"),
                "equity": round(float(st.get("equity", 0.0) or 0.0), 2),
                "cash_equiv": round(float(st.get("cash_equiv", 0.0) or 0.0), 2),
                "trades": len(st.get("trades") or []),
                "last_signal": st.get("last_signal_date"),
            }
    port_path = ROOT / "data" / "t2_portfolio_equity.jsonl"
    port = None
    if port_path.exists():
        rows = [json.loads(l) for l in port_path.read_text(encoding="utf-8").splitlines() if l]
        if rows:
            r = rows[-1]
            port = {"date": r.get("date"), "portfolio": r.get("portfolio"), "bh": r.get("bh")}
    return {"legs": legs, "portfolio": port}


def snap_freqtrade() -> dict:
    db = ROOT / "data" / "freqtrade" / "tradesv3.dryrun.sqlite"
    if not db.exists():
        return {"open": [], "closed": 0}
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        open_rows = con.execute(
            "SELECT pair, open_rate, close_profit_abs, open_date, stop_loss "
            "FROM trades WHERE is_open=1 ORDER BY id DESC").fetchall()
        closed = con.execute("SELECT COUNT(*) FROM trades WHERE is_open=0").fetchone()[0]
        con.close()
        return {"open": open_rows, "closed": closed}
    except Exception:
        return {"open": [], "closed": 0}


def snap_mm() -> dict:
    db = ROOT / "data" / "quant" / "orderbooks.sqlite"
    out = {}
    if db.exists():
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
            n = con.execute("SELECT COUNT(*) FROM snapshots_ws").fetchone()[0]
            span = con.execute("SELECT MAX(ts)-MIN(ts) FROM snapshots_ws").fetchone()[0] or 0
            nt = con.execute("SELECT COUNT(*) FROM trades_ws").fetchone()[0]
            out["snapshots"] = n
            out["span_h"] = round(span / 3600, 1)
            out["trade_flow"] = nt
            con.close()
        except Exception:
            pass
    qm = _read_json(ROOT / "data" / "reports" / "mm_queue_model.json", {})
    if qm and "BTC" in qm:
        btc = qm["BTC"].get("bid", {})
        out["btc_touch_life_s"] = btc.get("lifetime_median_s")
        fills = qm["BTC"].get("bid_fill", {}) or {}
        out["btc_fill60_q2000"] = fills.get("tau60s_q$2000")
    return out


def snap_scoreboard() -> dict | None:
    path = ROOT / "data" / "reports" / "strategy_scoreboard.jsonl"
    if not path.exists():
        return None
    try:
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
        return rows[-1] if rows else None
    except Exception:
        return None


def snap_services() -> dict[str, str]:
    out = {}
    try:
        proc = subprocess.run(["systemctl", "is-active", *SERVICES],
                              capture_output=True, text=True, timeout=30)
        states = proc.stdout.strip().split("\n") if proc.stdout.strip() else []
        for svc, st in zip(SERVICES, states):
            out[svc] = st
    except Exception:
        pass
    return out


def build_snapshot() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "directional": snap_directional(),
        "dca": snap_dca(),
        "basket": snap_basket(),
        "t2": snap_t2(),
        "freqtrade": snap_freqtrade(),
        "mm": snap_mm(),
        "scoreboard": snap_scoreboard(),
        "services": snap_services(),
    }


# -------------------------------------------------------------- formatting --
def format_report(snap: dict) -> list[str]:
    """HTML-отчёт кусками (Telegram-безопасными)."""

    lines = [
        "📊 <b>Детальный трейдинг-отчёт</b>",
        f"🕐 {snap['generated_at']}",
        "",
    ]

    # Directional v2 A/B
    d = snap["directional"]
    lines.append("⚖️ <b>Directional v2 paper (A/B)</b>")
    if d["ok"]:
        for tag in ("main", "control"):
            a = d["arms"].get(tag)
            if not a:
                continue
            icon = "🅰️" if tag == "main" else "🅱️"
            wr = f" (win {a['win_rate']}%)" if a["win_rate"] is not None else ""
            lines.append(
                f"{icon} <b>{tag}</b> (trail {'1.0' if tag == 'main' else '0.988'}): "
                f"{a['closed']} сд.{wr} | PnL {_fmt_usd(a['realized'])} "
                f"| gross {_fmt_usd(a['gross'])} | fees {_fmt_usd(a['fees'])}")
            lines.append(f"   equity {_fmt_usd(a['equity'])} | DD {a['dd_pct']:.3f}% "
                         f"| открытых: {a['open_positions']} | режим {a['entry_mode']}")
            for t in a["recent_trades"]:
                lines.append(
                    f"   • {t.get('exchange')}:{t.get('symbol')} {t.get('reason')} "
                    f"PnL {_fmt_usd(float(t.get('net_pnl_usd', 0.0) or 0.0))}")
    else:
        lines.append("нет данных")
    lines.append("")

    # DCA
    lines.append("📈 <b>DCA (еженедельный)</b>")
    for tag in ("VA main", "control"):
        a = snap["dca"].get(tag, {})
        if a.get("value") is None:
            continue
        pnl = a["value"] - (a["deposited"] or 0)
        pct = pnl / a["deposited"] * 100 if a["deposited"] else 0
        lines.append(
            f"• {tag} [{a['mode']}, ${a['weekly']}/нед]: "
            f"внесено {_fmt_usd(a['deposited'])} → {_fmt_usd(a['value'])} "
            f"({_fmt_usd(pnl)} / {pct:+.1f}%) | {a['date']}")
    lines.append("")

    # Basket
    b = snap["basket"]
    lines.append("🧺 <b>Корзина топ-10</b> (vol-targeting)")
    if b.get("value") is not None:
        lines.append(
            f"• {_fmt_usd(b['value'])} ({b['pnl_pct']:+.2f}%) | внесено {_fmt_usd(b['invested'])} "
            f"| fees {_fmt_usd(b['fees'])} | кэш {_fmt_usd(b['cash'])} | {b['date']}")
        lines.append(f"• правило весов: {b.get('weights_rule', '?')}")
    else:
        lines.append("нет данных")
    lines.append("")

    # T2 momentum
    t2 = snap["t2"]
    lines.append("📉 <b>T2 momentum paper</b> (SMA50-гистерезис, ежедневно)")
    for tag, leg in t2["legs"].items():
        pct = (leg["equity"] / 10000 - 1) * 100
        lines.append(
            f"• {tag}: {leg['position']} | equity {_fmt_usd(leg['equity'])} ({pct:+.1f}%) "
            f"| BH-эквив {_fmt_usd(leg['cash_equiv'])} | {leg['trades']} сд.")
    if t2["portfolio"]:
        p = t2["portfolio"]
        pct = (p["portfolio"] / 10000 - 1) * 100
        bh_pct = (p["bh"] / 10000 - 1) * 100
        lines.append(f"🧺 портфель T2: {_fmt_usd(p['portfolio'])} ({pct:+.1f}%) "
                     f"| BH {bh_pct:+.1f}% | {p['date']}")
    lines.append("")

    # Freqtrade
    ft = snap["freqtrade"]
    lines.append(f"🤖 <b>freqtrade T2 dry</b> (закрытых: {ft['closed']})")
    for row in ft["open"]:
        lines.append(f"• {row[0]}: открыта {row[3][:16]} @ {row[1]}, SL {row[4]}")
    if not ft["open"]:
        lines.append("открытых сделок нет")
    lines.append("")

    # MM
    m = snap["mm"]
    lines.append("🌊 <b>MM / микроструктура</b>")
    if m:
        lines.append(f"• ws-снапшотов: {m.get('snapshots', 0):,} ({m.get('span_h', 0)} ч), "
                     f"trade-flow: {m.get('trade_flow', 0):,}")
        if m.get("btc_touch_life_s"):
            lines.append(f"• BTC тач-жизнь {m['btc_touch_life_s']}с | "
                         f"fill(60с, $2000) {m.get('btc_fill60_q2000')}")
    else:
        lines.append("нет данных")
    lines.append("")

    # Scoreboard
    sb = snap["scoreboard"]
    if sb:
        v = sb.get("verdict") or {}
        w = v.get("winner", "—")
        if v.get("unstable"):
            w += " ⚠️"
        basket = sb.get("top10_basket_pct")
        basket_s = f"{basket:+.2f}%" if basket is not None else "—"
        lines.append(f"🏆 <b>Scoreboard {sb['date']}</b>: DV2 {sb['dv2']['pnl_pct']:+.2f}% | "
                     f"корзина {basket_s} | рынок {sb['market_mean_pct']:+.2f}% | 🥇 {w}")
        lines.append("")

    # Services
    svc = snap["services"]
    bad = [k for k, v in svc.items() if v != "active"]
    lines.append(f"🖥 <b>Сервисы:</b> {len(svc) - len(bad)}/{len(svc)} active"
                 + (f" | ⚠️ {', '.join(bad)}" if bad else ""))

    return _chunks("\n".join(lines))


# ------------------------------------------------------------------- LLM ----
def prompt_for_llm(snap: dict) -> str:
    """Компактный текстовый снапшот для LLM (без HTML)."""

    d = snap["directional"]
    parts = ["Состояние трейдинг-контуров AIOS (paper-only):"]
    for tag in ("main", "control"):
        a = d["arms"].get(tag)
        if not a:
            continue
        parts.append(
            f"Directional v2 {tag} (trail {'1.0' if tag == 'main' else '0.988'}): "
            f"{a['closed']} сделок, win {a['win_rate']}%, PnL {a['realized']:+.2f}$, "
            f"gross {a['gross']:+.2f}$, fees {a['fees']:.2f}$, equity {a['equity']}$, "
            f"DD {a['dd_pct']}%, открытых {a['open_positions']}")
    dca = snap["dca"]
    for tag in ("VA main", "control"):
        a = dca.get(tag, {})
        if a.get("value") is not None:
            pnl = a["value"] - (a["deposited"] or 0)
            parts.append(f"DCA {tag}: {a['deposited']}$ -> {a['value']}$ (PnL {pnl:+.2f}$)")
    b = snap["basket"]
    if b.get("value") is not None:
        parts.append(f"Корзина топ-10 (vol-targeting): {b['value']}$ ({b['pnl_pct']:+.2f}%), "
                     f"fees {b['fees']}$, правило {b['weights_rule']}")
    t2 = snap["t2"]
    for tag, leg in t2["legs"].items():
        pct = (leg["equity"] / 10000 - 1) * 100
        parts.append(f"T2 {tag}: {leg['position']}, equity {leg['equity']}$ ({pct:+.1f}%)")
    ft = snap["freqtrade"]
    parts.append(f"freqtrade T2 dry: {len(ft['open'])} открытых, {ft['closed']} закрытых")
    m = snap["mm"]
    if m:
        parts.append(f"ws-снапшотов {m.get('snapshots', 0):,} за {m.get('span_h', 0)} ч")
    sb = snap["scoreboard"]
    if sb:
        v = sb.get("verdict") or {}
        parts.append(f"Scoreboard {sb['date']}: победитель {v.get('winner')}")
    return "\n".join(parts)


SYSTEM_PROMPT = (
    "Ты — количественный аналитик торговой системы AIOS. Все контуры paper (без реальных "
    "денег). Известные результаты исследований системы: направленный edge на 1h не найден "
    "(ML AUC ~0.52-0.53, все эксперименты отрицательны); market-making edge нет; "
    "пассивная корзина топ-10 и DCA — единственные устойчиво положительные контуры; "
    "текущий режим рынка медвежий (BTC ниже SMA200). Отвечай строго по данным, не выдумывай. "
    "Формат ответа (русский, ≤900 символов): "
    "1) Риски — 3-5 пунктов по текущему состоянию; "
    "2) Анализ портфелей — что здорово/что слабо по цифрам; "
    "3) Сценарии-прогнозы — 3 варианта (вероятности %) на 1-2 недели с учётом медвежьего "
    "режима и отсутствия edge; в конце обязательная строка: 'Не является финансовым "
    "советом; paper-исследование'."
)


def llm_analysis(snap: dict) -> str | None:
    """LLM-аналитика и сценарии-прогнозы; None при недоступности LLM."""

    try:
        from aios_core.llm_balancer import LLMBalancer

        balancer = LLMBalancer()
        answer = balancer.chat(
            [{"role": "user", "content": prompt_for_llm(snap)}],
            system=SYSTEM_PROMPT,
            max_tokens=900,
            temperature=0.4,
            task_type="trading_report",
        )
        return (answer or "").strip() or None
    except Exception as exc:
        print(f"[trading_report] LLM недоступен: {exc}")
        return None


def llm_section(snap: dict) -> list[str]:
    """HTML-блок LLM-аналитики (куски, с дисклеймером)."""

    analysis = llm_analysis(snap)
    if not analysis:
        return ["🤖 <b>LLM-аналитика:</b> временно недоступна (балансер не ответил). "
                "Данные отчёта выше актуальны."]
    return _chunks("🤖 <b>LLM-аналитика и сценарии</b>\n" + analysis)


def full_report() -> list[str]:
    """Все сообщения для отправки: данные + LLM-аналитика."""

    snap = build_snapshot()
    return format_report(snap) + llm_section(snap)


if __name__ == "__main__":
    for msg in full_report():
        print("=" * 60)
        print(msg)
