#!/usr/bin/env python3
"""
Мониторинг расхода LLM-ключей: анализирует data/llm/usage.jsonl,
шлёт Telegram-алерт при аномальном расходе или приближении к лимитам.
Запуск по systemd-таймеру (раз в 6 часов).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "llm" / "usage_state.json"
USAGE_LOG = ROOT / "data" / "llm" / "usage.jsonl"
WARN_TOKEN_THRESHOLD = 10_000_000  # ~суточный потолок free-тира groq на org
WARN_RATE = 4000  # RPM аномалия (реальный потолок ~8000)


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
    req = urllib_request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib_request.urlopen(req, timeout=30):
        pass
    return True


import urllib.request as urllib_request  # noqa: E402


def analyze(alert: bool = True) -> dict:
    state = _read_state()
    now = time.time()
    out = {"total_calls": 0, "total_tokens": 0, "by_provider": {}, "alerts": []}

    if not USAGE_LOG.exists():
        return out

    day_ago = now - 86400
    hour_ago = now - 3600
    calls = 0
    tokens = 0
    provider_tokens: dict[str, int] = defaultdict(int)
    provider_calls: dict[str, int] = defaultdict(int)
    rpm_window: list[float] = []

    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        ts = rec.get("ts") or 0
        if ts < day_ago:
            continue
        calls += 1
        t = int(rec.get("total_tokens") or 0)
        tokens += t
        prov = str(rec.get("provider") or "?")
        provider_tokens[prov] += t
        provider_calls[prov] += 1
        if ts >= hour_ago:
            rpm_window.append(ts)

    out["total_calls"] = calls
    out["total_tokens"] = tokens
    out["by_provider"] = {
        p: {"calls": provider_calls[p], "tokens": provider_tokens[p]}
        for p in provider_calls
    }

    # Аномалия RPM за последний час
    rpm = len(rpm_window) / 60.0 if rpm_window else 0.0
    out["rpm_last_hour"] = round(rpm, 2)

    last_alert = float(state.get("last_alert_at") or 0)
    issues = []

    if tokens >= WARN_TOKEN_THRESHOLD:
        issues.append(f"🔺 Токенов за сутки: <b>{tokens:,}</b> (порог {WARN_TOKEN_THRESHOLD:,})")
    if rpm >= WARN_RATE:
        issues.append(f"🔺 Скорость: <b>{rpm:.0f} RPM</b> (порог {WARN_RATE})")

    if issues and alert and now - last_alert > 6 * 3600:
        text = "📊 <b>LLM-расход</b>\n" + "\n".join(issues) + "\n"
        if out["by_provider"]:
            top = sorted(out["by_provider"].items(), key=lambda x: -x[1]["tokens"])[:3]
            text += "\nТоп провайдеров (токены):\n" + "\n".join(
                f"• {p}: {v['tokens']:,}" for p, v in top
            )
        sent = _send(text)
        if sent:
            state["last_alert_at"] = now
            out["alerts"].append("sent")

    state["last_check_at"] = now
    _write_state(state)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM usage monitor")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-alert", action="store_true")
    args = parser.parse_args()

    if args.check:
        print(json.dumps(analyze(alert=not args.no_alert), ensure_ascii=False), flush=True)
        return

    while True:
        print(json.dumps(analyze(alert=not args.no_alert), ensure_ascii=False), flush=True)
        time.sleep(21600)


if __name__ == "__main__":
    main()
