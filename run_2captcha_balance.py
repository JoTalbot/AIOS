#!/usr/bin/env python3
"""
Мониторинг баланса 2captcha: алерт в Telegram при балансе < порога.
Запуск по systemd-таймеру (ежечасно): run_2captcha_balance.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # /root/AIOS
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "captcha_balance_state.json"
THRESHOLD = 5.0
CAPTCHA_KEY_FILE = ROOT / "data" / ".2captcha_key"


def _read_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(f".{STATE.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)
    try:
        STATE.chmod(0o600)
    except OSError:
        pass


def _captcha_key() -> str:
    try:
        key = CAPTCHA_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    except Exception:
        pass
    # env/ .env fallback
    env = os.environ.get("CAPTCHA_KEY", "") or os.environ.get("TWOCAPTCHA_KEY", "")
    if env:
        return env
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("CAPTCHA_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _fetch_balance(key: str) -> float | None:
    payload = json.dumps({"clientKey": key}).encode()
    req = urllib.request.Request(
        "https://api.2captcha.com/getBalance", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if data.get("errorId") != 0:
        return None
    return float(data.get("balance", 0.0))


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
    state = _read_state()
    key = _captcha_key()
    result = {"configured": bool(key), "balance": None, "alerted": False}

    if not key:
        result["error"] = "CAPTCHA_KEY не задан"
        return result

    try:
        balance = _fetch_balance(key)
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"fetch: {exc}"
        return result

    result["balance"] = balance
    last_alerted = float(state.get("last_alerted_balance") or 1e9)
    low = balance is not None and balance < THRESHOLD

    if low and alert and balance < last_alerted - 0.5:
        sent = _send(
            f"⚠️ <b>2captcha: низкий баланс</b>\n"
            f"Баланс: <b>${balance:.2f}</b> (порог ${THRESHOLD:.0f})\n"
            f"Пополните, иначе остановится создание ключей/капча."
        )
        result["alerted"] = sent
        state["last_alerted_balance"] = balance
        state["last_alert_at"] = int(time.time())
    if not low:
        state["last_alerted_balance"] = balance or 1e9

    state["balance"] = balance
    state["last_check_at"] = int(time.time())
    _write_state(state)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="2captcha balance monitor")
    parser.add_argument("--check", action="store_true", help="single check (для таймера)")
    parser.add_argument("--no-alert", action="store_true", help="без отправки алерта")
    args = parser.parse_args()

    if args.check:
        res = check(alert=not args.no_alert)
        print(json.dumps(res, ensure_ascii=False), flush=True)
        return

    while True:
        res = check(alert=not args.no_alert)
        print(json.dumps(res, ensure_ascii=False), flush=True)
        time.sleep(3600)


if __name__ == "__main__":
    main()
