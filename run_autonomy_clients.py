#!/usr/bin/env python3
"""
AIOS Autonomy Clients — сводка по клиентам и репутации.

  python run_autonomy_clients.py             # в stdout
  python run_autonomy_clients.py --send      # в Telegram
  python run_autonomy_clients.py --top 10    # показать N клиентов
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _tg(token: str, chat_id: int, text: str) -> None:
    import urllib.request
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def build(n: int) -> str:
    from aios_core.autonomy.report import client_summary
    c = client_summary()
    lines = [f"👥 <b>Клиенты автономии</b> (всего {c['total']})",
             f"trusted: {c['trusted']} · risky: {c['risky']} · new: {c['new']}", ""]
    for cl in c["clients"][-n:]:
        em = {"trusted": "🟢", "risky": "🔴", "known": "🟡", "new": "⚪"}.get(cl["trust"], "⚪")
        rep = cl["reputation"]
        lines.append(f"{em} {cl['chat'][:30]} | репутация {rep} | доверие {cl['trust']} | "
                     f"общений {cl['rounds']} | {cl.get('last_ts','')[:16]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    text = build(args.top)
    if args.send:
        token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
        chat_id = _env("TELEGRAM_CHAT_ID")
        if token and chat_id:
            _tg(token, int(chat_id), text)
            print("отправлено")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
