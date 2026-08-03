#!/usr/bin/env python3
"""
AIOS Autonomy Security — ежедневный отчёт по безопасности автономии.

Показывает: заблокированные инъекции, торг ниже пола, эскалации, блокировки.
  python run_autonomy_security.py            # вывод в stdout
  python run_autonomy_security.py --send     # отправить в Telegram
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


def build_report() -> str:
    from aios_core.autonomy.report import security_summary
    s = security_summary(days=1)
    lines = ["🔐 <b>Автономия: безопасность за сутки</b>", ""]
    lines.append(f"Попыток промпт-инъекции: <b>{s['injections']}</b>")
    if s["injection_by_chat"]:
        for k, v in s["injection_by_chat"].items():
            lines.append(f"  • {k}: {v}")
    lines.append(f"Торг ниже пола: {s['below_floor']}")
    lines.append(f"Эскалаций (на подтверждение): {s['escalations']}")
    lines.append(f"Блокировано: {s['blocked']}")
    lines.append(f"Авто-разрешено: {s['allowed']}")
    lines.append(f"\nВсего решений: {s['total']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="отправить в Telegram")
    args = ap.parse_args()
    text = build_report()
    if args.send:
        token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
        chat_id = _env("TELEGRAM_CHAT_ID")
        if token and chat_id:
            _tg(token, int(chat_id), text)
            print("отправлено")
        else:
            print("нет токена/чата")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
