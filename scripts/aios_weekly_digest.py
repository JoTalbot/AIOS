#!/usr/bin/env python3
"""V3: weekly digest of all quant/portfolio services to Telegram."""
from __future__ import annotations
import json, sqlite3, subprocess, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path("/root/AIOS")

def cred(name):
    p = Path("/etc/aios/credentials") / name
    return p.read_text().strip() if p.exists() else None

def send(text):
    t, c = cred("telegram_token"), cred("telegram_owner_chat_id")
    if not t or not c:
        print("no creds"); return False
    data = urllib.parse.urlencode({"chat_id": c, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{t}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get("ok", False)

def main():
    lines = ["📋 <b>AIOS Quant-дайджест</b>", ""]
    # DCA
    try:
        s = json.loads((ROOT/"data/dca_paper_state.json").read_text())
        vlog = [json.loads(l) for l in (ROOT/"data/dca_paper_value.jsonl").read_text().splitlines() if l]
        val = vlog[-1]["value_usd"] if vlog else 0
        dep = float(s.get("deposited_usd", 0))
        pnl = val - dep
        lines.append(f"📈 <b>DCA:</b> ${dep:.0f} → ${val:.2f} ({pnl:+.2f}$ / {pnl/dep*100 if dep else 0:+.1f}%)")
    except Exception as e:
        lines.append(f"📈 DCA: ошибка ({e})")
    # ws-данные
    try:
        con = sqlite3.connect(ROOT/"data/quant/orderbooks.sqlite")
        n = con.execute("SELECT COUNT(*) FROM snapshots_ws").fetchone()[0]
        h = (con.execute("SELECT MAX(ts)-MIN(ts) FROM snapshots_ws").fetchone()[0] or 0)/3600
        lines.append(f"🌊 <b>ws-данные:</b> {n:,} снапшотов ({h:.1f} ч)")
        con.close()
    except Exception as e:
        lines.append(f"🌊 ws: ошибка ({e})")
    # A/B paper
    try:
        m = json.loads((ROOT/"data/multi_exchange_portfolios_owner_paper.json").read_text())
        c = json.loads((ROOT/"data/multi_exchange_portfolios_owner_paper_control.json").read_text())
        tm = sum(p.get("total_trades", 0) for p in m.values() if isinstance(p, dict))
        tc = sum(p.get("total_trades", 0) for p in c.values() if isinstance(p, dict))
        lines.append(f"⚖️ <b>A/B paper:</b> main (trail 1.0) {tm} сделок | control (0.988) {tc}")
    except Exception as e:
        lines.append(f"⚖️ A/B: ошибка ({e})")
    # MM-сигналы: точность
    try:
        import subprocess as sp
        r = sp.run(["/opt/aios/.venv/bin/python", "scripts/mm_signal_score.py"],
                   capture_output=True, text=True, cwd="/root/AIOS")
        last = [l for l in r.stdout.strip().split("\n") if "ИТОГО" in l]
        lines.append(f"📡 <b>MM-сигналы:</b> {last[0] if last else 'нет данных'}")
    except Exception as e:
        lines.append(f"📡 MM: ошибка ({e})")
    # сервисы
    try:
        svc = subprocess.run(["systemctl", "is-active",
                              "aios-orderbook-ws.service", "aios-quant-trading.service",
                              "aios-quant-trading-control.service", "aios-dca-paper.timer",
                              "aios-dca-report.timer"], capture_output=True, text=True)
        st = svc.stdout.strip().split("\n")
        lines.append(f"🖥 <b>Сервисы:</b> {', '.join(st)}")
    except Exception as e:
        lines.append(f"🖥 сервисы: ошибка ({e})")
    ok = send("\n".join(lines))
    print("sent:", ok)

if __name__ == "__main__":
    main()
