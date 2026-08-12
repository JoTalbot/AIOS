#!/usr/bin/env python3
"""Internal Alertmanager webhook that sends and deletes a silent owner canary."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN_FILE = Path("/run/secrets/telegram_token")
CHAT_FILE = Path("/run/secrets/telegram_owner_chat_id")
STATE_FILE = Path("/state/state.json")
NONCE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def _telegram(method: str, payload: dict) -> dict:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("Telegram token credential is empty")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram API rejected canary")
    return result


def _write_state(payload: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="state.", dir=str(STATE_FILE.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, STATE_FILE)
    finally:
        tmp.unlink(missing_ok=True)


def deliver(nonce: str) -> dict:
    chat_id = int(CHAT_FILE.read_text(encoding="utf-8").strip())
    started = time.monotonic()
    sent = _telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "AIOS alert delivery canary",
            "disable_notification": True,
        },
    )
    message_id = int(sent.get("result", {}).get("message_id"))
    deleted = bool(
        _telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id}).get("result")
    )
    state = {
        "version": 1,
        "timestamp": time.time(),
        "nonce": nonce,
        "ok": deleted,
        "sent": True,
        "deleted": deleted,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    _write_state(state)
    return state


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/alert":
            self.send_error(404)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 1024 * 1024)
            body = json.loads(self.rfile.read(length))
            if body.get("status") != "firing":
                self.send_response(204)
                self.end_headers()
                return
            alerts = body.get("alerts") or []
            labels = alerts[0].get("labels", {}) if alerts else {}
            if labels.get("alertname") != "AIOSAlertmanagerDeliveryCanary":
                raise ValueError("unexpected alert")
            nonce = str(labels.get("canary_nonce", ""))
            if not NONCE.fullmatch(nonce):
                raise ValueError("invalid nonce")
            state = deliver(nonce)
            self.send_response(200 if state["ok"] else 502)
            self.end_headers()
        except (OSError, ValueError, RuntimeError, TypeError):
            self.send_error(400)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", 9099), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
