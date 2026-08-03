#!/usr/bin/env python3
"""
AIOS Autonomy Advice — рекомендации по ценовым полам (самообучение).

Только формирует предложения и шлёт владельцу — НЕ применяет автоматически.
Владелец подтверждает и сам вносит полы в data/price_floors.json
(или через бота).

  python run_autonomy_advice.py --send    # отправить в Telegram
  python run_autonomy_advice.py           # просто вывести в stdout
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="отправить в Telegram")
    args = ap.parse_args()

    from aios_core.autonomy.report import floor_advice
    adv = floor_advice()
    no_floor = adv.get("items_without_floor", [])
    sales = adv.get("recent_sales", [])

    lines = ["💡 <b>Рекомендации по ценовым полам</b>", ""]
    if no_floor:
        lines.append(f"Товаров без пола: {len(no_floor)}")
        for a in no_floor[:20]:
            lines.append(f"  • {a['item']} — цена {a['price']:.0f} → пол ≈ {a['suggested_floor']:.0f}")
    else:
        lines.append("Все товары склада имеют ценовой пол. 👍")
    if sales:
        lines.append("\nНедавние продажи:")
        for k, v in sales[:10]:
            lines.append(f"  • {k}: {v:.0f} грн")

    text = "\n".join(lines)
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
