#!/usr/bin/env python3
"""Rate-limited metadata-only Telegram alerts for new phone lead candidates."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

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


def _pending_rows() -> list[dict]:
    queue = AndroidLeadQueue(ROOT)
    queue.sync()
    return queue.list_pending(limit=300)


def check(alert: bool = False, bootstrap: bool = False) -> dict:
    rows = _pending_rows()
    state = _read(STATE, {"known_ids": []})
    known = {str(value) for value in (state.get("known_ids") or [])}
    new_rows = [row for row in rows if str(row.get("id") or "") not in known]
    current_ids = [str(row.get("id") or "") for row in rows if row.get("id")]
    by_source: dict[str, int] = {}
    for row in new_rows:
        source = str(row.get("source") or "Телефон")
        by_source[source] = by_source.get(source, 0) + 1
    sent = False
    if alert and new_rows and not bootstrap:
        summary = " · ".join(f"{source}: {count}" for source, count in sorted(by_source.items()))
        sent = _send(
            "📲 <b>Новые потенциальные лиды телефона</b>\n"
            f"Добавлено для проверки: <b>{len(new_rows)}</b>"
            + (f"\n{summary}" if summary else "")
            + "\n\n<i>Тексты, имена и номера не передавались. Команда: «лиды телефона».</i>"
        )
    # Keep a bounded union so reviewing old records cannot make a later lead
    # look old merely because the pending count changed.
    merged = list(dict.fromkeys((state.get("known_ids") or []) + current_ids))[-600:]
    _write(STATE, {
        "checked_at": _now(), "known_ids": merged,
        "pending": len(rows), "last_new": len(new_rows), "last_alert_sent": sent,
    })
    return {
        "status": "ok", "pending": len(rows), "new": len(new_rows),
        "by_source": by_source, "sent": sent, "bootstrap": bool(bootstrap),
    }


def main() -> int:
    args = set(sys.argv[1:])
    result = check(alert="--alert" in args, bootstrap="--bootstrap" in args)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
