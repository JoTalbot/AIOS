#!/usr/bin/env python3
"""
Автоучёт финансов из банковских SMS на телефоне (полуавтомат).

Каждые 10 минут смотрит новые уведомления банков из notifications.json:
если это поступление (поповнення/зарахування/надійшло…) с суммой —
ставит в очередь phone-brain задачу finance.book (kind=sale) БЕЗ confirm:
задача останавливается в need_confirm, владелец в TG говорит «подтверди N» —
запись проводится в data/finance.json. Без подтверждения ничего не пишется.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "finance_autobook_state.json"
NOTES = ROOT / "data" / "android_gateway" / "notifications.json"
BANK_PACKAGES = {"ua.com.abank": "A-Bank", "ua.privatbank.ap24": "Privat24"}
INCOME_RE = re.compile(r"(надійшло|надходження|поповнення|зарахуванн|поступлени|зачислени|отриман)", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(\d[\d\s]{0,6}(?:[.,]\d{1,2})?)\s*(?:грн|uah|грив)", re.IGNORECASE)
MAX_SEEN = 500


def _env(key: str) -> str:
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
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


def _tg(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": html.escape(text)[:3900], "parse_mode": "HTML"}
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except Exception:
        return False


def parse_income(text: str) -> float | None:
    """Сумма поступления из текста SMS/уведомления или None."""
    if not INCOME_RE.search(text or ""):
        return None
    m = AMOUNT_RE.search(text or "")
    if not m:
        return None
    try:
        value = float(m.group(1).replace(" ", "").replace(",", "."))
    except ValueError:
        return None
    return value if value > 0 else None


def run(dry: bool = False) -> dict:
    from aios_core.phone_brain.queue_store import JobStore

    try:
        notes = json.loads(NOTES.read_text(encoding="utf-8"))
    except Exception:
        notes = []
    state = {}
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        pass
    seen = set(state.get("seen") or [])
    store = JobStore(ROOT / "data" / "android_gateway" / "phone_brain.db")
    created = []
    for n in notes if isinstance(notes, list) else []:
        nid = str(n.get("id") or "")
        pkg = str(n.get("package") or "")
        if not nid or nid in seen or pkg not in BANK_PACKAGES:
            continue
        seen.add(nid)
        amount = parse_income(str(n.get("text") or "") + " " + str(n.get("title") or ""))
        if amount is None:
            continue
        payload = {"kind": "sale", "amount": amount,
                   "desc": f"Поступление ({BANK_PACKAGES[pkg]}, SMS-черновик)"}
        if dry:
            created.append({"job_id": None, "amount": amount, "app": BANK_PACKAGES[pkg]})
            continue
        job = store.enqueue("finance.book", payload)
        job_id = job.get("id") if isinstance(job, dict) else None
        created.append({"job_id": job_id, "amount": amount, "app": BANK_PACKAGES[pkg]})
        _tg(f"💰 <b>{BANK_PACKAGES[pkg]}</b>: поступление {amount:.0f} грн. "
            f"Черновик продажи #{job_id} ждёт: «подтверди {job_id}» — и запись уйдёт в финансы.")
    state["seen"] = list(seen)[-MAX_SEEN:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok", "created": created}


def main() -> int:
    import sys
    dry = "--dry" in sys.argv
    result = run(dry=dry)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
