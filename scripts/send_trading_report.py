#!/usr/bin/env python3
"""Send the detailed trading report (Трейдинг button content) to the owner's
Telegram chat: data chunks immediately, LLM section after generation."""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/root/AIOS")
sys.path.insert(0, str(ROOT))


def _env(key: str) -> str:
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
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


def _post(payload: dict, token: str) -> tuple[bool, str]:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return bool(data.get("ok")), data.get("description", "")
    except urllib.error.HTTPError as exc:
        return False, exc.read().decode(errors="replace")[:300]
    except Exception as exc:
        return False, str(exc)


def tg_send(text: str) -> tuple[bool, str]:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID") or _env("AIOS_OWNER_CHAT_ID")
    if not token or not chat:
        return False, "no credentials"
    base = {
        "chat_id": int(chat),
        "text": text[:3900],
        "disable_web_page_preview": True,
    }
    ok, err = _post({**base, "parse_mode": "HTML"}, token)
    if ok:
        return True, ""
    # HTML-режим мог сломаться о символы в LLM-тексте — ретрай без разметки
    ok2, err2 = _post(base, token)
    return ok2, f"html:{err[:80]}; plain:{err2[:120]}"


def main() -> int:
    from tg_bot.trading_report import full_report

    messages = full_report()
    sent = 0
    for i, msg in enumerate(messages, 1):
        ok, err = tg_send(msg)
        if ok:
            sent += 1
            print(f"chunk {i}/{len(messages)}: sent ({len(msg)} chars)")
        else:
            print(f"chunk {i}/{len(messages)}: FAIL {err[:200]}")
    print(f"total sent: {sent}/{len(messages)}")
    return 0 if sent == len(messages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
