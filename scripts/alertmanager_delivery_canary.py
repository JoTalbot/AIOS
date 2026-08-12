#!/usr/bin/env python3
"""Verify Alertmanager -> internal webhook -> Telegram silent send/delete."""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALERTMANAGER = os.environ.get("AIOS_ALERTMANAGER_URL", "http://127.0.0.1:9093").rstrip("/")
STATE_FILE = Path(os.environ.get("AIOS_ALERT_CANARY_STATE", "/var/lib/aios-alert-canary/state.json"))


def _post_alert(nonce: str, *, resolve: bool = False) -> None:
    now = datetime.now(timezone.utc)
    ends = now if resolve else now + timedelta(minutes=2)
    payload = [
        {
            "labels": {
                "alertname": "AIOSAlertmanagerDeliveryCanary",
                "severity": "info",
                "canary_nonce": nonce,
            },
            "annotations": {"summary": "AIOS end-to-end alert delivery canary"},
            "startsAt": now.isoformat().replace("+00:00", "Z"),
            "endsAt": ends.isoformat().replace("+00:00", "Z"),
            "generatorURL": "",
        }
    ]
    request = urllib.request.Request(
        ALERTMANAGER + "/api/v2/alerts",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status not in (200, 202):
            raise RuntimeError("Alertmanager rejected canary")


def _state() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def main() -> int:
    nonce = secrets.token_hex(12)
    _post_alert(nonce)
    deadline = time.monotonic() + float(os.environ.get("AIOS_ALERT_CANARY_TIMEOUT", "45"))
    result: dict = {}
    try:
        while time.monotonic() < deadline:
            result = _state()
            if result.get("nonce") == nonce:
                break
            time.sleep(0.5)
    finally:
        try:
            _post_alert(nonce, resolve=True)
        except Exception:
            pass
    ok = bool(
        result.get("nonce") == nonce
        and result.get("ok")
        and result.get("sent")
        and result.get("deleted")
    )
    print(
        "alertmanager_delivery_canary=" + ("success" if ok else "failure")
        + " sent=" + ("yes" if result.get("sent") else "no")
        + " deleted=" + ("yes" if result.get("deleted") else "no")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
