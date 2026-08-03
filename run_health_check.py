#!/usr/bin/env python3
"""
AIOS Health Check — проверяет все systemd-сервисы/таймеры AIOS, диск,
и шлёт уведомление в Telegram при проблемах. Запуск по таймеру.
  python run_health_check.py [--silent]  # --silent: только при проблемах
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SERVICES = ["aios-telegram-bot", "aios-dashboard-v3", "aios-dashboard-v2", "aios-olx-collector",
            "aios-selfguard", "aios-auto-coder"]
TIMERS = ["aios-np-alert.timer", "aios-olx-price.timer", "aios-post-scheduler.timer",
          "aios-analytics.timer", "aios-digest.timer", "aios-evening-report.timer",
          "aios-backup-sessions.timer", "aios-olx-autoreply.timer", "aios-local-backup.timer"]


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(token: str, chat_id: int, text: str) -> None:
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def check() -> dict:
    problems = []
    ok_count = 0

    for svc in SERVICES:
        try:
            r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=15)
            st = (r.stdout or "").strip()
            if st != "active":
                # замаскированные сервисы выключены намеренно — не считаем проблемой
                r2 = subprocess.run(["systemctl", "is-enabled", svc], capture_output=True, text=True, timeout=15)
                if (r2.stdout or "").strip() == "masked":
                    continue
            if st == "active":
                ok_count += 1
            else:
                problems.append(f"🔴 сервис {svc}: {st}")
        except Exception as e:
            problems.append(f"🔴 сервис {svc}: ошибка проверки {e}")

    for t in TIMERS:
        try:
            r = subprocess.run(["systemctl", "is-active", t], capture_output=True, text=True, timeout=15)
            st = (r.stdout or "").strip()
            if st == "active":
                ok_count += 1
            else:
                problems.append(f"🔴 таймер {t}: {st}")
        except Exception as e:
            problems.append(f"🔴 таймер {t}: ошибка {e}")

    # диск
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=10)
        line = r.stdout.strip().splitlines()[-1]
        parts = line.split()
        pct = parts[4].rstrip("%") if len(parts) > 4 else "0"
        if int(pct) >= 80:
            problems.append(f"🔴 Диск заполнен на {pct}% ({parts[3]})")
        else:
            ok_count += 1
    except Exception:
        pass

    return {"ok": ok_count, "problems": problems, "total": ok_count + len(problems)}


def main() -> int:
    silent = "--silent" in sys.argv
    res = check()
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")

    print(f"Здоровье: OK {res['ok']}/{res['total']}, проблем: {len(res['problems'])}")
    for p in res["problems"]:
        print(" ", p)

    if not token or not chat:
        return 1
    if res["problems"]:
        txt = "🏥 <b>AIOS Health Check</b> — найдены проблемы:\n" + "\n".join(res["problems"])
        try:
            _tg(token, int(chat), txt)
            print("Алерт отправлен")
        except Exception as e:
            print("Ошибка алерта:", e)
    elif not silent:
        try:
            _tg(token, int(chat), f"🏥 <b>AIOS Health Check</b>: всё в порядке ✅ ({res['ok']}/{res['total']})")
        except Exception:
            pass
    return 0 if not res["problems"] else 2


if __name__ == "__main__":
    sys.exit(main())
