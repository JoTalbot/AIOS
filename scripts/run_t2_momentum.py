#!/usr/bin/env python3
"""T2 momentum paper-loop: daily signal (BTC close vs SMA50) + state + TG alerts.

Backtest-proven strategy (docs/MOMENTUM_STRATEGIES_RESULT_2026-08-16_RU.md):
long BTC while close > SMA50 (1d), cash otherwise. This paper loop runs daily:

  1. fetch daily closes (Yahoo BTC-USD, fallback Binance spot);
  2. compute SMA50 over CLOSED bars only;
  3. signal for today = last closed close > SMA50 (same rule as the backtest);
  4. if position changes -> apply 0.15% cost, log the trade, notify Telegram;
  5. mark equity daily (close/close) and append to value log.

State: data/t2_paper_state.json ; history: data/t2_paper_equity.jsonl
Idempotent: re-running the same day does not double-log.

Usage:
    python run_t2_momentum.py [--notify] [--state FILE] [--log FILE]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

def _urls(symbol: str) -> tuple[str, str]:
    """Yahoo and Binance URLs for a symbol like 'BTC-USD' / 'ETH-USD'."""
    base = symbol.split("-")[0].upper()
    binance_sym = base + "USDT"
    return (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=400d&interval=1d",
            f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=1d&limit=400")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SMA_W = 50
COST = 0.0015  # per side, same as backtest


def default_transport(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_closes(transport=None, symbol: str = "BTC-USD") -> list[dict]:
    """List of {date, close} for closed daily bars (oldest first)."""
    t = transport or default_transport
    yahoo_url, binance_url = _urls(symbol)
    errs = []
    # primary: Yahoo
    try:
        raw = t(yahoo_url)
        data = json.loads(raw.decode())
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        close = res["indicators"]["quote"][0]["close"]
        rows = []
        for x, c in zip(ts, close):
            if c is None:
                continue
            rows.append({"date": time.strftime("%Y-%m-%d", time.gmtime(x)),
                         "close": float(c)})
        if len(rows) >= 100:
            return rows
        errs.append(f"yahoo: only {len(rows)} rows")
    except Exception as e:
        errs.append(f"yahoo: {e}")
    # fallback: Binance spot
    try:
        raw = t(binance_url)
        klines = json.loads(raw.decode())
        rows = []
        for k in klines:
            rows.append({"date": time.strftime("%Y-%m-%d", time.gmtime(k[0] / 1000)),
                         "close": float(k[4])})
        if len(rows) >= 100:
            return rows
        errs.append(f"binance: only {len(rows)} rows")
    except Exception as e:
        errs.append(f"binance: {e}")
    raise RuntimeError("; ".join(errs))


def sma(closes: list[float], w: int) -> float | None:
    if len(closes) < w:
        return None
    return sum(closes[-w:]) / w


def check_price_discrepancy(rows: list[dict], transport=None) -> str | None:
    """Cross-check the last close from Yahoo vs Binance spot; warn if > 0.5% off."""
    if not rows:
        return None
    t = transport or default_transport
    sym = "BTCUSDT" if "BTC" in rows[-1].get("_sym", "BTC-USD") else "ETHUSDT"
    try:
        import urllib.parse
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
        raw = t(url)
        binance_close = float(json.loads(raw.decode())["price"])
        yahoo_close = rows[-1]["close"]
        diff = abs(binance_close - yahoo_close) / yahoo_close * 100
        if diff > 0.5:
            return (f"⚠️ Расхождение цен {sym}: Yahoo {yahoo_close:.2f} vs "
                    f"Binance {binance_close:.2f} ({diff:.2f}%)")
    except Exception:
        return None
    return None


def compute_signal(rows: list[dict]) -> dict:
    """Signal based on the LAST CLOSED bar (no lookahead)."""
    closes = [r["close"] for r in rows]
    last = rows[-1]
    s50 = sma(closes, SMA_W)
    if s50 is None:
        return {"date": last["date"], "close": last["close"], "sma50": None,
                "signal": "CASH", "reason": "not_enough_history"}
    sig = "LONG" if last["close"] > s50 else "CASH"
    return {"date": last["date"], "close": last["close"], "sma50": round(s50, 2),
            "signal": sig, "reason": "close_gt_sma50" if sig == "LONG" else "close_le_sma50"}


class T2State:
    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            self.data = json.loads(path.read_text())
        else:
            self.data = {"position": "CASH", "entry_date": None, "entry_price": None,
                         "equity": 10000.0, "last_signal_date": None,
                         "trades": [], "cash_equiv": 10000.0}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))
        tmp.replace(self.path)


def run_daily(state_path: Path, log_path: Path, rows: list[dict], notify=None) -> dict:
    """One daily step: compute signal, update state, log, notify on change."""
    st = T2State(state_path)
    sig = compute_signal(rows)
    last = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else None

    # idempotency: already processed this bar?
    if st.data.get("last_signal_date") == sig["date"]:
        # just re-mark equity and return current state
        return {"status": "already_processed", "signal": sig["signal"],
                "equity": st.data["equity"]}

    # mark previous day's PnL first (close/close while in position)
    if prev is not None and st.data["position"] == "LONG" and st.data["entry_price"]:
        st.data["equity"] *= last["close"] / prev["close"]
    # buy&hold reference (cash_equiv = always-long equity, for comparison)
    if prev is not None:
        st.data["cash_equiv"] = st.data.get("cash_equiv", 10000.0) * last["close"] / prev["close"]

    # position change? cost applies on ANY transition (same as backtest)
    if st.data["position"] != sig["signal"]:
        old = st.data["position"]
        st.data["equity"] *= (1.0 - COST)
        if sig["signal"] == "LONG":
            st.data["entry_price"] = last["close"]
            st.data["entry_date"] = sig["date"]
        else:
            st.data["entry_price"] = None
            st.data["entry_date"] = None
        st.data["position"] = sig["signal"]
        st.data["trades"].append({"date": sig["date"], "from": old, "to": sig["signal"],
                                  "close": last["close"], "sma50": sig["sma50"],
                                  "equity": round(st.data["equity"], 2)})
        if notify:
            notify(sig, old)
    st.data["last_signal_date"] = sig["date"]
    st.save()

    # append to value log
    bh_equity = st.data.get("cash_equiv", 10000.0)
    entry = {"date": sig["date"], "close": last["close"], "sma50": sig["sma50"],
             "signal": sig["signal"], "position": st.data["position"],
             "equity": round(st.data["equity"], 2),
             "bh_equity": round(bh_equity, 2)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "ok", "signal": sig["signal"], "position": st.data["position"],
            "equity": st.data["equity"], "sma50": sig["sma50"], "close": last["close"]}


def tg_send(text: str) -> bool:
    token_p = Path("/etc/aios/credentials/telegram_token")
    chat_p = Path("/etc/aios/credentials/telegram_owner_chat_id")
    if not token_p.exists() or not chat_p.exists():
        return False
    token, chat = token_p.read_text().strip(), chat_p.read_text().strip()
    import urllib.parse
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception:
        return False


def daily_report(symbol: str, state_path: Path) -> str | None:
    """One-line daily report (position, equity, BH) - sent every day."""
    st = T2State(state_path).data
    eq = float(st.get("equity", 10000.0))
    bh = float(st.get("cash_equiv", 10000.0))
    pct = (eq / 10000 - 1) * 100
    bh_pct = (bh / 10000 - 1) * 100
    tag = symbol.replace("-", "")
    return (f"📈 T2-{tag} {time.strftime('%Y-%m-%d')}: {st.get('position')} | "
            f"equity ${eq:,.0f} ({pct:+.1f}%) | BH {bh_pct:+.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC-USD")
    ap.add_argument("--state", type=Path, default=None)
    ap.add_argument("--log", type=Path, default=None)
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--daily-report", action="store_true",
                    help="send a one-line report every run (not only on change)")
    ap.add_argument("--transport", default=None, help="injectable (tests)")
    args = ap.parse_args()

    sym_tag = args.symbol.replace("-", "").lower()
    if args.state is None:
        args.state = Path(f"/root/AIOS/data/t2_paper_state_{sym_tag}.json")
    if args.log is None:
        args.log = Path(f"/root/AIOS/data/t2_paper_equity_{sym_tag}.jsonl")

    rows = fetch_closes(args.transport, args.symbol)
    warn = check_price_discrepancy(rows, args.transport)
    if warn:
        tg_send(warn)
    if args.daily_report:
        report = daily_report(args.symbol, args.state)
        if report:
            tg_send(report)
    def notify(sig, old):
        txt = (f"📈 T2-сигнал: {sig['date']}\n"
               f"{old} -> {sig['signal']} | close {sig['close']:.0f} SMA50 {sig['sma50']}\n"
               f"причина: {sig['reason']}")
        tg_send(txt)
    res = run_daily(args.state, args.log, rows, notify if args.notify else None)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
