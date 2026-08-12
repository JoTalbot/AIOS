#!/usr/bin/env python3
"""Rate-limited metadata-only Telegram alerts for new phone lead candidates."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from aios_core.android_bank_monitor import AndroidBankMonitor
from aios_core.android_leads import AndroidLeadQueue

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "android_gateway" / "lead_digest_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _env(name: str) -> str:
    if name in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if name in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
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
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30):
        pass
    return True


def _queue_snapshot() -> tuple[list[dict], dict]:
    queue = AndroidLeadQueue(ROOT)
    queue.sync()
    return queue.list_pending(limit=300), queue.summary()


def _bank_tasks() -> list[dict]:
    return AndroidBankMonitor(ROOT).list_tasks(limit=300)


def check(alert: bool = False, bootstrap: bool = False) -> dict:
    rows, summary = _queue_snapshot()
    bank_tasks = _bank_tasks()
    state = _read(STATE, {"known_ids": []})
    known = {str(value) for value in (state.get("known_ids") or [])}
    new_rows = [row for row in rows if str(row.get("id") or "") not in known]
    current_ids = [str(row.get("id") or "") for row in rows if row.get("id")]
    known_bank_ids = {str(value) for value in (state.get("known_bank_task_ids") or [])}
    new_bank_tasks = [task for task in bank_tasks if str(task.get("id") or "") not in known_bank_ids]
    current_bank_ids = [str(task.get("id") or "") for task in bank_tasks if task.get("id")]
    by_source: dict[str, int] = {}
    for row in new_rows:
        source = str(row.get("source") or "Телефон")
        by_source[source] = by_source.get(source, 0) + 1
    previous_overdue = int(state.get("crm_overdue") or 0)
    crm_open = int(summary.get("crm_open") or 0)
    crm_attention = int(summary.get("crm_attention") or 0)
    crm_overdue = int(summary.get("crm_overdue") or 0)
    overdue_increased = crm_overdue > previous_overdue
    sent = False
    if alert and not bootstrap and (new_rows or new_bank_tasks or overdue_increased):
        source_summary = " · ".join(f"{source}: {count}" for source, count in sorted(by_source.items()))
        lines = ["📲 <b>Телефонные лиды и CRM follow-up</b>"]
        if new_rows:
            lines.append(f"Новых карточек для проверки: <b>{len(new_rows)}</b>" + (f" · {source_summary}" if source_summary else ""))
        if crm_open:
            lines.append(f"Открытых CRM follow-up: <b>{crm_open}</b> · внимание: {crm_attention} · просрочены: {crm_overdue}")
        if new_bank_tasks:
            lines.append(f"Новых локальных банковских задач: <b>{len(new_bank_tasks)}</b>")
        lines.append("<i>Содержимое чатов, суммы, карты, OTP, имена и номера не передавались.</i>")
        sent = _send("\n".join(lines))
    # Keep a bounded union so reviewing old records cannot make a later lead
    # look old merely because the pending count changed.
    merged = list(dict.fromkeys((state.get("known_ids") or []) + current_ids))[-600:]
    merged_bank = list(dict.fromkeys((state.get("known_bank_task_ids") or []) + current_bank_ids))[-600:]
    _write(STATE, {
        "checked_at": _now(), "known_ids": merged, "known_bank_task_ids": merged_bank,
        "pending": len(rows), "last_new": len(new_rows), "last_bank_new": len(new_bank_tasks), "last_alert_sent": sent,
        "crm_open": crm_open, "crm_attention": crm_attention, "crm_overdue": crm_overdue,
    })
    return {
        "status": "ok", "pending": len(rows), "new": len(new_rows), "bank_new": len(new_bank_tasks),
        "by_source": by_source, "sent": sent, "bootstrap": bool(bootstrap),
        "crm_open": crm_open, "crm_attention": crm_attention, "crm_overdue": crm_overdue,
    }


def main() -> int:
    args = set(sys.argv[1:])
    result = check(alert="--alert" in args, bootstrap="--bootstrap" in args)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
