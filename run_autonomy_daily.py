#!/usr/bin/env python3
"""
AIOS Autonomy Daily — ежедневная сводка автономии в Telegram.

Запуск по таймеру (systemd). Показывает: авто/эскалации/блокировки,
продажи через автономию, активные approval, аномалии.
"""
from __future__ import annotations

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
    from aios_core.autonomy.report import daily_summary, anomalies, floor_advice, security_summary, client_summary

    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("нет токена/чата")
        return 0

    s = daily_summary(days=1)
    lines = ["📊 <b>Автономия: сводка за сутки</b>", ""]
    lines.append(f"Решений всего: {s['total_decisions']}")
    for k, v in sorted(s["by_decision"].items(), key=lambda x: -x[1]):
        lines.append(f"  • {k}: {v}")
    if s["sales"]:
        lines.append(f"\n💰 Продаж через автономию: {s['sales']} на {s['sales_amount']} грн")
    lines.append("\nАктивные действия:")
    try:
        ap = json.loads((ROOT / "data" / "autonomy_approvals.json").read_text(encoding="utf-8"))
        pending = [a for a in ap if a.get("status") == "pending"]
        lines.append(f"  • ожидают решения: {len(pending)}")
    except Exception:
        pass

    anom = anomalies()
    if anom:
        lines.append("\n🚨 Аномалии:")
        for a in anom[:4]:
            lines.append(f"  • {a.get('note', a.get('type'))}")

    adv = floor_advice()
    no_floor = adv.get("items_without_floor", [])
    if no_floor:
        lines.append(f"\n💡 Нет ценового пола у {len(no_floor)} товаров со склада "
                     f"(рекомендации — run_autonomy_advice.py)")

    # Безопасность
    sec = security_summary(days=1)
    lines.append(f"\n🔐 <b>Безопасность:</b> инъекций {sec['injections']} · ниже пола {sec['below_floor']} "
                 f"· эскалаций {sec['escalations']} · блокировок {sec['blocked']}")
    if sec["injections"]:
        lines.append("  (команда /security для деталей)")

    # Клиенты
    cl = client_summary()
    lines.append(f"\n👥 <b>Клиенты:</b> {cl['total']} · trusted {cl['trusted']} · risky {cl['risky']} · new {cl['new']}")
    if cl["risky"]:
        lines.append("  (команда /reputation для списка)")

    _tg(token, int(chat_id), "\n".join(lines))
    print("сводка отправлена")
    return 0


if __name__ == "__main__":
    sys.exit(main())
