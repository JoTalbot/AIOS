#!/usr/bin/env python3
"""
Мониторинг диска: Telegram-алерт при заполнении > 85%.
Запуск: systemd timer (раз в 6 часов).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "disk_state.json"
THRESHOLD = 85.0


def _env(name: str) -> str:
    from tg_bot.credentials import read_systemd_credential

    if name in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _send(text: str) -> bool:
    from tg_bot.credentials import secret_from_env_or_credential

    token = secret_from_env_or_credential("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30):
        pass
    return True


def check(alert: bool = True) -> dict:
    usage = shutil.disk_usage("/")
    pct = usage.used / usage.total * 100.0
    free_gb = usage.free / 1024**3
    out = {"pct": round(pct, 1), "free_gb": round(free_gb, 1)}

    state = {}
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        pass

    last_alert = float(state.get("last_alert_at") or 0)
    if pct >= THRESHOLD and alert and time.time() - last_alert > 6 * 3600:
        sent = _send(
            f"💾 <b>Диск заполнен на {pct:.0f}%</b>\n"
            f"Свободно: <b>{free_gb:.1f} ГБ</b>\n"
            f"Почистите: <code>cd /root/AIOS && du -sh backups/ Calls/ data/ | sort -rh</code>"
        )
        out["alerted"] = sent
        state["last_alert_at"] = time.time()

    state["last_check_at"] = int(time.time())
    state["pct"] = round(pct, 1)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(f".{STATE.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="disk monitor")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-alert", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(alert=not args.no_alert), ensure_ascii=False), flush=True)
        return
    while True:
        print(json.dumps(check(alert=True), ensure_ascii=False), flush=True)
        time.sleep(21600)


if __name__ == "__main__":
    main()
